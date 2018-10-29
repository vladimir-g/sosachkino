import os
import logging
import asyncio
import datetime
import pytz
import sqlalchemy as sa
from collections import defaultdict
from aiopg.sa import create_engine
from sqlalchemy.dialects import postgresql as pg

from sosachkino.db.models import *

logger = logging.getLogger(__name__)


class DB:
    """Wrapper for sqlite database."""
    def __init__(self, db_config):
        self.db_config = db_config

    async def init(self, app):
        """Init database engine."""
        logger.info('Initializing database with config %s',
                    dict(self.db_config))
        self.engine = await create_engine(**self.db_config)
        logger.info('Database initialized')

    async def shutdown(self, app):
        """Close database connection."""
        logger.info('Shutting down database')
        self.engine.close()

    async def get_state(self, board, thread_ids=None):
        """Get current saved state for every thread in board."""
        q = sa.select([Threads]).where(Threads.board == board)
        if thread_ids is not None and len(thread_ids):
            q = q.where(Threads.id.in_(thread_ids))
        state = {}
        async with self.engine.acquire() as conn:
            async for row in conn.execute(q):
                state[row['id']] = row
        return state

    async def update_thread_state(self, board, thread, last_id):
        """Update thread in database after check."""
        data = dict(
            subject=thread.get('subject', thread['num']),
            last=last_id,
            updated=datetime.datetime.now(),
            files_count=thread['files_count'],
            board=board,
            id=int(thread['num'])
        )
        q = pg.insert(Threads.__table__).values(**data).\
            on_conflict_do_update(
                constraint='threads_unique',
                set_=data
            )
        async with self.engine.acquire() as conn:
            await conn.execute(q)

    async def save_videos(self, files):
        """Insert new videos into database."""
        timezone = pytz.timezone('Europe/Moscow')
        for f in files:
            keys = ('size', 'width', 'height', 'thumbnail', 'tn_height',
                    'tn_width', 'path', 'md5', 'thread', 'board')
            name = os.path.splitext(f.get('fullname', f['name']))[0]
            values = {k: f[k] for k in keys}
            values.update({
                'name': name,
                'timestamp': datetime.datetime.fromtimestamp(
                    f['timestamp'],
                    tz=timezone
                ),
                'id': int(''.join([c for c in f['name'] if c.isdigit()]))
            })
            q = pg.insert(Files.__table__).values(**values).\
                on_conflict_do_update(
                    constraint='files_unique',
                    set_=values
                )
            logger.debug('File: board %s, checksum %s', f['board'], f['md5'])
            async with self.engine.acquire() as conn:
                await conn.execute(q)

    def filter_query(self, query, filter_):
        """Get filtered query for video list."""
        if 'board' in filter_:
            query = query.where(Files.board.in_(filter_['board']))
        if 'thread' in filter_:
            query = query.where(Files.thread.in_(filter_['thread']))
        return query

    async def get_videos_count(self, filter_=dict()):
        """Get list of videos with filter."""
        q = sa.select([sa.func.count(Files.id)]).select_from(Files)
        q = self.filter_query(q, filter_)
        async with self.engine.acquire() as conn:
            result = await conn.scalar(q)
        return result

    async def get_threads(self, filter_=dict()):
        """Get list of threads with videos count."""
        # Get filter info grouped with file counts
        q = sa.select([
            Threads.id,
            Threads.board,
            Threads.subject,
            sa.func.count(Files.id).label('files')
        ]).select_from(
            Files.__table__.join(Threads, Files.thread == Threads.id)
        ).having(sa.func.count(Files.id) > 0).\
        order_by(sa.func.count(Files.id).desc()).\
        group_by(Threads.id)

        # Filter it by our common filter but remove thread param
        filtered = None
        if filter_ and 'thread' in filter_:
            try:
                filtered = [int(i) for i in filter_['thread']] # For sorting
            except:
                pass
            filter_ = filter_.copy()
            del filter_['thread']
        threads = []
        async with self.engine.acquire() as conn:
            async for row in conn.execute(self.filter_query(q, filter_)):
                threads.append(dict(row))
        if filtered is not None:
            threads = sorted(threads,
                             key=lambda t: (t['id'] in filtered, t['files']),
                             reverse=True)
        return threads

    async def get_videos(self, filter_=dict()):
        """Get list of videos with filter, generator."""
        q = sa.select([
            Files,
            Threads.subject
        ]).select_from(
            Files.__table__.join(Threads, Threads.id == Files.thread)
        ).order_by(Files.timestamp.desc())
        q = self.filter_query(q, filter_)
        if 'limit' in filter_:
            q = q.limit(filter_['limit'])
        if 'offset' in filter_:
            q = q.offset(filter_['offset'])

        async with self.engine.acquire() as conn:
            async for row in conn.execute(q):
                yield dict(row)

    async def set_removed(self, board, thread_ids):
        """Set removed date for threads that don't exist in catalog now."""
        logger.debug('Marking old threads as removed, board: /%s/', board)
        async with self.engine.acquire() as conn:
            await conn.execute(
                sa.update(Threads)
                .where(~Threads.id.in_(thread_ids))
                .where(Threads.removed_date == None)
                .where(Threads.board == board)
                .values(removed_date=datetime.datetime.now())
            )

    async def get_boards(self):
        """Get list of existing boards."""
        boards = set()
        q = sa.select([sa.distinct(Threads.board)])
        async with self.engine.acquire() as conn:
            async for row in conn.execute(q):
                boards.add(row[0])
        return sorted(boards)

    async def get_removed_thread_check(self, from_date):
        """Get files from removed threads that need checking."""
        q = sa.select([Files]).select_from(
            Files.__table__.join(Threads, Threads.id == Files.thread)
        ).where(Threads.removed_date < datetime.datetime.now()).\
        where(Files.last_check < from_date).\
        order_by(Files.last_check.asc())
        files = []
        async with self.engine.acquire() as conn:
            async for row in conn.execute(q):
                files.append(dict(row))
        logger.debug('Found %s potentially missing files', len(files))
        return files

    async def get_files_to_check(self, from_date):
        """Get files that just need check."""
        # Check newer files first
        q = sa.select([Files]).\
            where(Files.last_check < from_date).\
            order_by(Files.last_check.desc()).\
            limit(60)      # Don't check everything in one run
        files = []
        async with self.engine.acquire() as conn:
            async for row in conn.execute(q):
                files.append(dict(row))
        logger.debug('Got %s old files', len(files))
        return files

    async def remove_file(self, file_id):
        """Remove file from database."""
        logger.debug('Removing file %s', file_id)
        async with self.engine.acquire() as conn:
            await conn.execute(
                sa.delete(Files).where(Files.id == file_id)
            )

    async def update_checked(self, file_id):
        """Remove file from database."""
        logger.debug('Update last check for file %s', file_id)
        async with self.engine.acquire() as conn:
            await conn.execute(
                sa.update(Files).where(Files.id == file_id)
                .values(last_check=datetime.datetime.now())
            )

    async def clean_threads(self):
        """Remove threads without files from database."""
        logger.debug('Cleaning old threads')
        async with self.engine.acquire() as conn:
            await conn.execute(
                sa.delete(Threads).where(Threads.id.in_(
                    sa.select([Threads.id]).select_from(
                        Threads.__table__.outerjoin(Files, Files.thread == Threads.id)
                    ).where(Threads.removed_date.isnot(None))
                    .group_by(Threads.id)
                    .having(sa.func.count(Files.id) == 0))
                )
            )
