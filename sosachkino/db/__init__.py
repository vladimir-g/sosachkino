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
            last=last_id,
            updated=datetime.datetime.utcnow(),
            files_count=thread['files_count'],
            board=board,
            id=thread_id
        )
        await self.conn.execute(q)

    # async def cleanup(self, board, thread_ids):
    #     """Remove old threads from database. We assuming that thread never
    #     appears in catalog once it is gone."""
    #     await self.conn.execute(sa.delete(Threads).
    #                             where(Threads.board == board).
    #                             where(~Threads.id.in_(thread_ids)))

    async def save_videos(self, files):
        """Insert new videos into database."""
        checksums = defaultdict(list)
        # Get already existing files with same md5 for same boards
        for f in files:
            checksums[f['board']].append(f['md5'])
        existing = set()
        for board, md5_list in checksums.items():
            c = await self.conn.execute(
                sa.select([Files.md5])
                .where(Files.md5.in_(md5_list))
                .where(Files.board == board)
            )
            res = await c.fetchall()
            for row in res:
                existing.add((board, row['md5']))
        
        for f in files:
            keys = ('size', 'width', 'height', 'thumbnail', 'tn_height',
                    'tn_width', 'path', 'md5', 'thread', 'board')
            values = {k: f[k] for k in keys}
            values.update({
                'name': f['fullname'][:-5], # strip .webm
                'timestamp': datetime.datetime.fromtimestamp(f['timestamp'])
            })
            if (f['board'], f['md5']) in existing:
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

    async def get_videos(self):
        """Get list of videos with filter."""
        res = await self.conn.execute(
            sa.select([Files]).order_by(Files.timestamp.desc()).limit(50)
        )
        while True:
            row = await res.fetchone()
            if row is None:
                break
            yield dict(row)
