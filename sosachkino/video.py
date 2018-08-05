import os
import datetime
from urllib.parse import urljoin

from sosachkino.api import Api


class Video:
    """Wrapper around video database row."""
    types = {
        'webm': 'video/webm',
        'mp4': 'video/mp4'
    }

    def __init__(self, data):
        self.data = data

    @property
    def url(self):
        """Get full video URL."""
        return urljoin(Api.base_url, self.data['path'])

    @property
    def thumbnail(self):
        """Get full thumbnail URL."""
        return urljoin(Api.base_url, self.data['thumbnail'])

    @property
    def date(self):
        """Get datetime from internal file timestamp."""
        return self.data['timestamp']

    def __getitem__(self, key):
        """Get field from internal row."""
        return self.data[key]

    @property
    def type(self):
        """Get video mime type by path."""
        spl = os.path.splitext(self.data['path'])
        if not len(spl) == 2:
            return None
        # Without leading dot
        return self.types.get(spl[1][1:], None)

    @property
    def board(self):
        """Get board."""
        return '/{}/'.format(self.data['board'])
    
    @property
    def thread(self):
        """Get thread with board."""
        return '/{}/{}'.format(self.data['board'], self.data['thread'])

    @property
    def subject(self):
        """Get thread subject."""
        return self.data['subject']

    def thread_link(self, app, query=None):
        """Get link filtered by thread."""
        q = dict(thread=self.data['thread'])
        if query is not None and 'limit' in query:
            q['limit'] = query['limit']
        return app.router['videos'].url_for().with_query(q)
