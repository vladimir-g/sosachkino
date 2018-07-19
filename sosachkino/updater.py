import logging
import asyncio
import time


logger = logging.getLogger(__name__)


class Updater:
    """Object that checks for new videos and updates database."""
    is_running = False
    last_check = None

    def __init__(self, config, api, db):
        self.db = db
        self.config = config
        self.api = api

    async def update(self, boards=None):
        """Check for new webms."""
        self.is_running = True
        if boards is None:
            boards = [b.strip() for b in
                      self.config['app']['boards'].split(',')]
        for board in boards:
            await self.update_board(board)
        self.last_check = time.time() # Maybe asyncio.loop.time()?
        self.is_running = False

    async def update_board(self, board):
        """Get list of threads and process every thread."""
        logger.info('Updating board /%s/', board)
        threads = await self.api.get_catalog(board)
        thread_ids = [int(thread['num']) for thread in threads]
        state = await self.db.get_state(board, thread_ids)
        files = []
        interval = int(self.config['app']['sleep_interval'])
        await asyncio.sleep(interval)
        for thread in threads:
            thread_id = int(thread['num'])

            # Check if thread must be skipped
            is_changed = self.is_changed(state, thread)
            is_ignored = self.is_ignored(state, thread)
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
            data = await self.api.get_thread(board, thread_id, from_id)
            # Process posts
            last_id = thread_id
            for post in data:
                for f in post['files']:
                    if not f['path'].lower().endswith('.webm'):
                        continue
                    f.update({
                        'thread': int(thread['num']),
                        'board': board,
                        'timestamp': int(post['timestamp'])
                    })
                    files.append(f)
                last_id = int(post['num'])

            await self.db.update_thread_state(board, thread, last_id)
            # Sleep for configured time
            await asyncio.sleep(interval)
        logger.info('Got %s new videos for /%s/', len(files), board)
        await self.db.save_videos(files)
        await self.db.cleanup(board, thread_ids)

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
        if thread_id in state:
            return state[thread_id]['hidden']
        return False

    def needs_update(self):
        """Check if check interval already passed since last check."""
        if self.is_running:
            return False
        if self.last_check is None:
            return True
        return (time.time() - self.last_check >
                int(self.config['app']['check_interval']))

    async def run(self, app):
        """Run endless check loop."""
        try:
            # Maybe call_later or more robust implementation of check
            # will be better?
            if self.config['app'].get('disable_updater', False):
                logger.info('Updater is disabled in config')
                return
            while True:
                if self.needs_update():
                    logger.info('Starting periodic update run')
                    await self.update()
                else:
                    logger.info('Skipping update run')
                await asyncio.sleep(int(self.config['app']['check_interval']))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Error on update run: %s", e)

    @classmethod
    async def start_task(cls, app):
        """Start background check task."""
        app['check_task'] = app.loop.create_task(app['updater'].run(app))
        
    @classmethod
    async def cleanup_task(cls, app):
        """Stop background check task."""
        app['check_task'].cancel()
        await app['check_task']
