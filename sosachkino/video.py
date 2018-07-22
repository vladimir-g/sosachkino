import datetime
from urllib.parse import urljoin

from sosachkino.api import Api


class Video:
    """Wrapper around video database row."""
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
        return datetime.datetime.fromtimestamp(self.data['timestamp'])

    def __getitem__(self, key):
        """Get field from internal row."""
        return self.data[key]
