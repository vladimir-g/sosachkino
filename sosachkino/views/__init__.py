import math


def page_range(page, size):
    """Get range of displayed pages."""
    r = lambda begin, end: list(range(begin, end))
    near = 3
    if size <= (near * 2) or (page - near <= near and
                             page + near >= size - near):
        # [1 size]
        page_range = [r(1, size + 1)]
    elif page > size or page < 1:
        # [1 near] ...  [-near size]
        page_range = [r(1, near + 1),
                      r(size - near + 1, size + 1)]
    elif page - near <= near:
        # [1 page + near] ... [-near size]
        page_range = [r(1, page + near + 1),
                      r(size - near + 1, size + 1)]

    elif page + near > size - near:
        # [1 near] ... [page - near size]
        page_range = [r(1, near + 1),
                      r(page - near + 1, size + 1)]
    else:
        # [1 near] ... [page - near page + near] ... [-near size]
        page_range = [r(1, near + 1),
                      r(page - near, page + near + 1),
                      r(size - near + 1, size + 1)]
    return page_range


class BaseView:
    """Base class for all views."""
    def __init__(self, app):
        self.app = app

    def get_pagination(self, route, page, count,
                       page_size, query=None, kw=None):
        """Get list of paginated links."""
        if query is None: query = dict()
        if kw is None: kw = dict()

        def get_query_for_page(p):
            q = query.copy()
            q['page'] = str(p)
            return q

        pages = math.ceil(count / page_size)
        list_ = []
        for group in page_range(page, pages):
            block = []
            for p in group:
                query = get_query_for_page(p)
                link = self.app.router[route].\
                    url_for(**kw).\
                    with_query(**query)
                block.append({
                    'number': str(p),
                    'link': link,
                    'current': page == p
                })
            list_.append(block)
        prev = None
        if page != 1:
            prev = dict(
                link=self.app.router[route]
                .url_for(**kw)
                .with_query(**get_query_for_page(page - 1))
            )
        next_ = None
        if page != pages:
            next_ = dict(
                link=self.app.router[route]
                .url_for(**kw)
                .with_query(**get_query_for_page(page + 1))
            )
        return {
            'pages': list_,
            'current': page,
            'count': pages,
            'prev': prev,
            'next': next_
        }
