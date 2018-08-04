import os
import logging
import asyncio
import datetime
import sqlalchemy as sa
from collections import defaultdict
from sqlalchemy_aio import ASYNCIO_STRATEGY

from sosachkino.db.models import *

logger = logging.getLogger(__name__)


class DB:
    """Wrapper for sqlite database."""
    def __init__(self, conn_string):
        self.conn_string = conn_string

    async def init(self, app):
        """Init database connection and create tables."""
        logger.info('Initializing database with config %s', self.conn_string)
        self.engine = sa.create_engine(self.conn_string,
                                       strategy=ASYNCIO_STRATEGY)
        self.conn = await self.engine.connect()
        logger.info('Database initialized')

    async def shutdown(self, app):
        """Close database connection."""
        logger.info('Shutting down database')
        await self.conn.close()

    async def get_state(self, board, thread_ids=None):
        """Get current saved state for every thread in board."""
        q = sa.select([Threads]).where(Threads.board == board)
        if thread_ids is not None and len(thread_ids):
            q = q.where(Threads.id.in_(thread_ids))
        result = await self.conn.execute(q)
        threads = await result.fetchall()
        state = {row['id']: row for row in threads}
        return state

    async def update_thread_state(self, board, thread, last_id):
        """Update thread in database after check."""
        thread_id = int(thread['num'])
        query = sa.select([sa.exists().
                           where(Threads.id == thread_id).
                           where(Threads.board == board)])
        res = await self.conn.scalar(query)
        if res:
            # Update existingthread
            q = sa.update(Threads).where(Threads.id == thread_id)
        else:
            # Insert new thread
            q = Threads.__table__.insert()
        q = q.values(
            subject=thread.get('subject', thread['num']),
            last=last_id,
            updated=datetime.datetime.now(),
            files_count=thread['files_count'],
            board=board,
            id=thread_id
        )
        await self.conn.execute(q)

    async def save_videos(self, files):
        """Insert new videos into database."""
        checksums = defaultdict(list)
        # Get already existing files with same md5 for same boards
        for f in files:
            checksums[f['board']].append(f['md5'])
        existing = defaultdict(set)
        for board, md5_list in checksums.items():
            c = await self.conn.execute(
                sa.select([Files.md5])
                .where(Files.md5.in_(md5_list))
                .where(Files.board == board)
            )
            res = await c.fetchall()
            for row in res:
                existing[board].add(row['md5'])
        for f in files:
            keys = ('size', 'width', 'height', 'thumbnail', 'tn_height',
                    'tn_width', 'path', 'md5', 'thread', 'board')
            name = os.path.splitext(f.get('fullname', f['name']))[0]
            values = {k: f[k] for k in keys}
            values.update({
                'name': name,
                'timestamp': datetime.datetime.fromtimestamp(f['timestamp'])
            })
            if f['md5'] in existing[f['board']]:
                q = sa.update(Files).\
                    where(Files.board == f['board']).\
                    where(Files.md5 == f['md5'])
                logger.debug('Updating file: board %s, checksum %s',
                             f['board'], f['md5'])
            else:
                q = Files.__table__.insert()
                logger.debug('Inserting file: board %s, checksum %s',
                             f['board'], f['md5'])
                values['id'] = int(''.join(
                    [c for c in f['name'] if c.isdigit()]
                ))
            await self.conn.execute(q.values(**values))

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
        result = await self.conn.scalar(q)
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
        res = await self.conn.execute(
            self.filter_query(q, filter_)
        )
        result = await res.fetchall()
        threads = [dict(row) for row in result]
        if filtered is not None:
            threads = sorted(threads,
                             key=lambda t: (t['id'] in filtered, t['files']),
                             reverse=True)
        return threads

    async def get_videos(self, filter_=dict()):
        """Get list of videos with filter."""
        q = sa.select([Files]).order_by(Files.timestamp.desc())
        q = self.filter_query(q, filter_)
        if 'limit' in filter_:
            q = q.limit(filter_['limit'])
        if 'offset' in filter_:
            q = q.offset(filter_['offset'])

        res = await self.conn.execute(q)
        while True:
            row = await res.fetchone()
            if row is None:
                break
            yield dict(row)

    async def set_removed(self, board, thread_ids):
        """Set removed date for threads that don't exist in catalog now."""
        logger.debug('Marking old threads as removed, board: /%s/', board)
        await self.conn.execute(
            sa.update(Threads)
            .where(~Threads.id.in_(thread_ids))
            .where(Threads.removed_date == None)
            .where(Threads.board == board)
            .values(removed_date=datetime.datetime.now())
        )

    async def get_boards(self):
        """Get list of existing boards."""
        boards = set()
        c = await self.conn.execute(
            sa.select([sa.distinct(Threads.board)])
        )
        result = await c.fetchall()
        for row in result:
            boards.add(row[0])
        return sorted(boards)

    async def get_removed_thread_check(self, from_date):
        """Get files from removed threads that need checking."""
        c = await self.conn.execute(
            sa.select([Files]).select_from(
                Files.__table__.join(Threads, Threads.id == Files.thread)
            ).where(Threads.removed_date < datetime.datetime.now())
            .where(Files.last_check < from_date)
            .order_by(Files.last_check.asc())
        )
        res = await c.fetchall()
        files = [dict(f) for f in res]
        logger.debug('Found %s potentially missing files', len(files))
        return files

    async def get_files_to_check(self, from_date):
        """Get files that just need check."""
        c = await self.conn.execute(
            sa.select([Files])
            .where(Files.last_check < from_date)
            .order_by(Files.last_check.desc()) # Check newer files first
            .limit(60)      # Don't check everything in one run
        )
        res = await c.fetchall()
        files = [dict(f) for f in res]
        logger.debug('Got %s old files', len(files))
        return files

    async def remove_file(self, file_id):
        """Remove file from database."""
        logger.debug('Removing file %s', file_id)
        await self.conn.execute(
            sa.delete(Files).where(Files.id == file_id)
        )

    async def update_checked(self, file_id):
        """Remove file from database."""
        logger.debug('Update last check for file %s', file_id)
        await self.conn.execute(
            sa.update(Files).where(Files.id == file_id)
            .values(last_check=datetime.datetime.now())
        )

    async def clean_threads(self):
        """Remove threads without files from database."""
        logger.debug('Cleaning old threads')
        await self.conn.execute(
            sa.delete(Threads).where(Threads.id.in_(
                sa.select([Threads.id]).select_from(
                    Threads.__table__.outerjoin(Files, Files.thread == Threads.id)
                ).group_by(Threads.id)
                .having(sa.func.count(Files.id) == 0))
            )
        )
