import aiohttp_jinja2

from sosachkino.views import BaseView
from sosachkino.video import Video


class VideosView(BaseView):
    """Videos-related views."""
    page_size = 24

    def get_int_param(self, query, name, default):
        """Get integer parameter from query with fallback value."""
        value = default
        try:
            value = int(query.get(name))
        except (TypeError, ValueError) as e:
            pass
        return value

    @aiohttp_jinja2.template("videos/list.jinja2")
    async def list(self, request):
        """Paginated and filtrable list of videos."""
        query = request.query;
        videos = []
        
        # Filtering
        q = dict()
        if 'board' in query:
            q['board'] = query.getall('board')
        if 'thread' in query:
            q['thread'] = query.getall('thread')

        # Page and page size
        page_size = self.get_int_param(query, 'limit', self.page_size)
        page = self.get_int_param(query, 'page', 1)

        q['limit'] = page_size
        q['offset'] = (page - 1) * page_size

        boards = await request.app['db'].get_boards()
        # Now get the videos
        async for video in request.app['db'].get_videos(q):
            videos.append(Video(video))

        count = await request.app['db'].get_videos_count(q)

        pagination = self.get_pagination(
            'videos', page, count, page_size, query
        )

        return {
            'videos': videos,
            'boards': boards,
            'pagination': pagination,
            'query': q
        }
