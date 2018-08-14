import logging
import asyncio
import datetime
import time

from sosachkino.api import ApiError


logger = logging.getLogger(__name__)


class Updater:
    """Object that checks for new videos and updates database."""
    is_running = False
    last_check = None
    is_running_cleanup = False
    last_check_cleanup = None
    extensions = ('.webm', '.mp4')

    def __init__(self, config, api, db):
        self.db = db
        self.config = config
        self.api = api

    async def update(self, boards=None):
        """Check for new webms."""
        self.is_running = True
        if boards is None:
            boards = [b.strip() for b in
                      self.config['updater']['boards'].split(',')]
        for board in boards:
            await self.update_board(board)
        self.last_check = time.time() # Maybe asyncio.loop.time()?
        self.is_running = False

    async def update_board(self, board):
        """Get list of threads and process every thread."""
        logger.info('Updating board /%s/', board)
        try:
            threads = await self.api.get_catalog(board)
        except ApiError as e:
            logger.warning("Couldn't get /%s/ catalog: %s", board, e)
            return
        except Exception as e:
            logger.exception("Error while getting catalog: %s", e)
            return
        thread_ids = [int(thread['num']) for thread in threads]
        state = await self.db.get_state(board, thread_ids)
        interval = int(self.config['updater']['sleep'])
        await asyncio.sleep(interval)
        for thread in threads:
            thread_id = int(thread['num'])

            # Check if thread must be skipped
            is_changed = self.is_changed(state, thread)
            is_ignored = self.is_ignored(state, thread) # FIXME
            if not is_changed or is_ignored:
                logger.debug(
                    "Skipping thread /%s/%s, changed: %s, ignored: %s",
                    board, thread_id, is_changed, is_ignored
                )
                continue

            logger.debug('Processing thread /%s/%s', board, thread['num'])
            # Get last checked post
            from_id = None
            if thread_id in state:
                from_id = state[thread_id]['last']
            # FIXME process this
            try:
                data = await self.api.get_thread(board, thread_id, from_id)
            except ApiError as e:
                logger.warning("Couldn't get thread /%s/%s : %s",
                               board, thread_id, e)
                continue
            except Exception as e:
                logger.exception("Error while processing thread /%s/%s: %s",
                                 board, thread_id, e)
                continue

            # Check API error, maybe move to api later FIXME
            if isinstance(data, dict):
                if 'Error' in data and 'Code' in data:
                    logger.warning("Response error /%s/%s : %s",
                                   board, thread_id, data)
                    continue

            # Process posts
            files = []
            try:
                last_id = thread_id
                for post in data:
                    for f in post['files']:
                        if not self.is_video(f['path']):
                            continue
                        f.update({
                            'thread': int(thread['num']),
                            'board': board,
                            'timestamp': int(post['timestamp'])
                        })
                        files.append(f)
                    last_id = int(post['num'])

                await self.db.update_thread_state(board, thread, last_id)
                if len(files):
                    logger.info('Saving %s new videos for /%s/',
                                len(files), board)
                    await self.db.save_videos(files)
                    files = []
            except Exception as e:
                logger.exception("Error while processing posts /%s/%s: %s",
                                 board, thread_id, e)
                continue

            # Sleep for configured time
            await asyncio.sleep(interval)
        await self.db.set_removed(board, thread_ids)
        await self.db.clean_threads()

    def is_changed(self, state, thread):
        """Check if thread was changed from last update."""
        thread_id = int(thread['num'])
        # TODO: something more interesting that files_count
        if thread_id in state:
            if state[thread_id]['files_count'] != thread['files_count']:
                return True
        else:
            return True
        return False

    def is_ignored(self, state, thread):
        """Check if thread is ignored and must be skipped."""
        thread_id = int(thread['num'])
        # if thread_id in state:
        #     return state[thread_id]['hidden']
        return False

    def needs_update(self):
        """Check if check interval already passed since last check."""
        if self.is_running:
            return False
        if self.last_check is None:
            return True
        return (time.time() - self.last_check >
                int(self.config['updater']['interval']))

    def needs_cleanup(self):
        """Check if cleanup interval already passed since last run."""
        if self.is_running_cleanup:
            return False
        if self.last_check_cleanup is None:
            return True
        return (time.time() - self.last_check_cleanup >
                int(self.config['cleanup']['interval']))

    async def cleanup(self):
        """Check for removed webms."""
        self.is_running_cleanup = True
        from_date = datetime.datetime.now() - datetime.timedelta(
            seconds=int(self.config['cleanup']
                        .get('removed_thread_check_time', 3600))
        )
        check_files = await self.db.get_removed_thread_check(from_date)
        # If all threads are ok, just check some newer files
        if not len(check_files):
            from_date = datetime.datetime.now() - datetime.timedelta(
                seconds=int(self.config['cleanup']
                            .get('file_check_time', 14400))
            )
            check_files = await self.db.get_files_to_check(from_date)
        logger.debug('Checking %s files', len(check_files))
        interval = int(self.config['cleanup']['sleep'])
        for f in check_files:
            try:
                exists = await self.api.check_file(f['path'])
                if not exists:
                    await self.db.remove_file(f['id'])
                else:
                    await self.db.update_checked(f['id'])
            except ApiError as e:
                logger.warning("Couldn't check %s: %s", f['path'], e)
            except Exception as e:
                logger.exception("Error while checking %s: %s", f['path'], e)
            # Cleand threads when there is no update
            if not self.is_running:
                await self.db.clean_threads()
            await asyncio.sleep(interval)
        self.last_check_cleanup = time.time()
        self.is_running_cleanup = False

    async def run_update(self, app):
        """Run endless check loop."""
        try:
            # Maybe call_later or more robust implementation of check
            # will be better?
            if self.config['updater'].getboolean(
                    'disable', fallback=False
            ):
                logger.info('Updater is disabled in config')
                return
            while True:
                if self.needs_update():
                    logger.info('Starting periodic update run')
                    await self.update()
                    logger.info('Finished periodic update run')
                else:
                    logger.info('Skipping update run')
                await asyncio.sleep(int(self.config['updater']['interval']))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error on update run: %s", e)

    async def run_cleanup(self, app):
        """Run endless clean loop."""
        try:
            if self.config['cleanup'].getboolean(
                    'disable', fallback=False
            ):
                logger.info('Cleanup is disabled in config')
                return
            while True:
                if self.needs_cleanup():
                    logger.info('Starting periodic cleanup run')
                    await self.cleanup()
                    logger.info('Finished periodic cleanup run')
                else:
                    logger.info('Skipping cleanup run')
                await asyncio.sleep(
                    int(self.config['cleanup'].get('interval', 300))
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error on cleanup run: %s", e)

    @classmethod
    async def start_task(cls, app):
        """Start background tasks."""
        app['check_task'] = app.loop.create_task(
            app['updater'].run_update(app)
        )
        app['cleanup_task'] = app.loop.create_task(
            app['updater'].run_cleanup(app)
        )

    @classmethod
    async def cleanup_task(cls, app):
        """Stop background tasks."""
        app['check_task'].cancel()
        app['cleanup_task'].cancel()
        await app['check_task']
        await app['cleanup_task']

    def is_video(self, path):
        """Check if file is supported video format."""
        lpath = path.lower()
        for ext in self.extensions:
            if lpath.endswith(ext): return True
        return False
