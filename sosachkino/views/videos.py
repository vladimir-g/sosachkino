import aiohttp_jinja2

from sosachkino.views import BaseView
from sosachkino.video import Video


class VideosView(BaseView):
    """Videos-related views."""
    @aiohttp_jinja2.template("videos/list.jinja2")
    async def list(self, request):
        """Paginated and filtrable list of videos."""
        videos = []
        async for video in request.app['db'].get_videos():
            videos.append(Video(video))
        return {
            'videos': videos
        }
