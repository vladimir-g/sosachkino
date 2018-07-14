import logging
import asyncio


logger = logging.getLogger(__name__)


class Updater:
    """Object that checks for new videos and updates database."""
    is_running = False

    def __init__(self, config, api, db):
        self.db = db
        self.config = config

    async def update(self, boards=None):
        """Check for new webms."""
        self.is_running = True
        if boards is None:
            boards = self.config['app']['boards']
        for board in boards:
            await self.update_board(board)
        self.is_running = False

    async def update_board(self, board):
        """Get list of threads and process every thread."""
        threads = await self.api.get_catalog(board)
        thread_ids = [int(thread['num']) for thread in threads]
        state = await self.db.get_state(board, thread_ids)
        files = []
        await asyncio.sleep(self.config['app']['sleep_interval'])
        for thread in threads:
            is_changed = self.is_changed(state, thread)
            is_ignored = self.is_ignored(state, thread)
            if not changed or ignored:
                logger.debug("Skipping thread %s, changed: %s, ignored: %s",
                             thread['num'], is_changed, is_ignored)
                continue
            logger.debug('Processing thread %s', thread['num'])
            data = await self.api.get_thread(board, thread['num'])
            for post in data:
                files.extend([f for f in post['files']
                              if f['path'].endswith('.webm')])
            await self.db.update_thread_state(thread)
            # Sleep for configured time
            await asyncio.sleep(self.config['app']['sleep_interval'])
        logger.info('Got %s new videos', len(files))
        await self.db.insert_videos(board, files)
        print(files)
