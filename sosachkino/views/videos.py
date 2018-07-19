import aiohttp_jinja2

from sosachkino.views import BaseView


class VideosView(BaseView):
    """Videos-related views."""
    @aiohttp_jinja2.template("videos/list.jinja2")
    async def list(self, request):
        """Paginated and filtrable list of videos."""
        return {
            'videos': await request.app['db'].get_videos()
        }
