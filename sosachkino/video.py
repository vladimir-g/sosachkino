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
