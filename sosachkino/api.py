import logging
from urllib.parse import urlencode
from aiohttp import ClientSession, ClientError


logger = logging.getLogger(__name__)


class ApiError(Exception):
    """API-related exception."""
    def __init__(self, message, url):
        super().__init__(message)
        self.url = url

    def __str__(self):
        err = super().__str__()
        return '{}, url: {}'.format(err, self.url)


class Api:
    """Partially implemented sosach API."""
    base_url = 'https://2ch.hk'

    async def init(self, app):
        self.session = ClientSession()

    async def close(self, app):
        await self.session.close()

    def get_url(self, path, query=dict()):
        """Create url for path and optional query."""
        url = self.base_url.rstrip('/') + path
        if query:
            url = '{}?{}'.format(url, urlencode(query))
        return url

    def catalog_url(self, board):
        """Create url for catalog file."""
        return self.get_url('/{}/catalog.json'.format(board))

    def thread_url(self, board, thread, from_):
        """Create url for thread."""
        return self.get_url('/makaba/mobile.fcgi', dict(
            task='get_thread',
            board=board,
            thread=thread,
            num=from_
        ))

    def file_url(self, path):
        """Create url for video file."""
        return self.get_url(path)

    async def get_catalog(self, board):
        """Get thread list from catalog."""
        url = self.catalog_url(board)
        logger.debug('Requesting catalog %s', url)
        try:
            async with self.session.get(url) as r:
                response = await r.json()
                return response['threads']
        except ClientError as e:
            logger.warning('API error: url %s, %s', url, e)
            raise ApiError(e, url)

    async def get_thread(self, board, thread, from_=None):
        """Get messages from thread starting with from_ post."""
        if from_ is None:
            from_ = thread
        url = self.thread_url(board, thread, from_)
        logger.debug('Requesting thread %s', url)
        try:
            async with self.session.get(url) as r:
                response = await r.json()
                return response
        except ClientError as e:
            logger.warning('API error: url %s, %s', url, e)
            raise ApiError(e, url)

    async def check_file(self, path):
        """Check if file exists at link."""
        url = self.file_url(path)
        logger.debug('Checking file %s', url)
        try:
            async with self.session.head(url, allow_redirects=True) as r:
                if r.status != 200:
                    return False
            return True
        except ClientError as e:
            logger.warning('API error: url %s, %s', url, e)
            raise ApiError(e, url)
