import aiohttp_jinja2

from sosachkino.views import BaseView
from sosachkino.video import Video


class VideosView(BaseView):
    """Videos-related views."""
    page_size = 24

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
        try:
            page_size = int(query.get('limit', self.page_size))
        except (TypeError, ValueError) as e:
            pass

        try:
            page = int(query.get('page', 1))
        except (TypeError, ValueError) as e:
            pass

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
