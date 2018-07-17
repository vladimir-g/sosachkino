import logging
from urllib.parse import urlencode
from aiohttp import ClientSession


logger = logging.getLogger(__name__)


class Api:
    """Partially implemented sosach API."""
    base_url = 'https://2ch.hk'

    async def init(self, app):
        self.session = ClientSession()

    async def close(self, app):
        await self.session.close()

    def get_url(self, path, query=dict()):
        url = self.base_url.rstrip('/') + path
        if query:
            url = '{}?{}'.format(url, urlencode(query))
        return url

    def catalog_url(self, board):
        return self.get_url('/{}/catalog.json'.format(board))

    def thread_url(self, board, thread, from_):
        return self.get_url('/makaba/mobile.fcgi', dict(
            task='get_thread',
            board=board,
            thread=thread,
            num=from_
        ))

    async def get_catalog(self, board):
        """Get thread list from catalog."""
        url = self.catalog_url(board)
        logger.debug('Requesting catalog %s', url)
        async with self.session.get(url) as r:
            response = await r.json()
            return response['threads']

    async def get_thread(self, board, thread, from_=None):
        """Get messages from thread starting with from_ post."""
        if from_ is None:
            from_ = thread
        url = self.thread_url(board, thread, from_)
        logger.debug('Requesting thread %s', url)
        async with self.session.get(url) as r:
            response = await r.json()
            return response
