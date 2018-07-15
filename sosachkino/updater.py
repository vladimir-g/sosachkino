import logging
import asyncio


logger = logging.getLogger(__name__)


class Updater:
    """Object that checks for new videos and updates database."""
    is_running = False

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
        self.is_running = False

    async def update_board(self, board):
        """Get list of threads and process every thread."""
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
                logger.debug("Skipping thread %s, changed: %s, ignored: %s",
                             thread_id, is_changed, is_ignored)
                continue

            logger.debug('Processing thread %s', thread['num'])
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
        logger.info('Got %s new videos', len(files))
        await self.db.save_videos(files)
        await self.db.cleanup(board, thread_ids)

    def is_changed(self, state, thread):
        """Check if thread was changed from last update."""
        thread_id = int(thread['num'])
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
