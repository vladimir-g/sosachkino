import logging
import asyncio
import datetime
import aiosqlite
import sqlite3
from collections import defaultdict


logger = logging.getLogger(__name__)


class DB:
    """Wrapper for sqlite database."""
    def __init__(self, path):
        self.path = path

    def get_db(self):
        """Get aiosqlite database connection. Connector is used directly here to
        set row factory."""
        def connector():
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            return conn
        return aiosqlite.Connection(connector, asyncio.get_event_loop())

    async def init(self, app):
        """Init database connection and create tables."""
        logger.info('Initializing database at %s', self.path)
        async with self.get_db() as db:
            await db.execute(
                r'''
                CREATE TABLE IF NOT EXISTS threads ( 
                id integer PRIMARY KEY,
                board text,
                last integer,
                files_count integer,
                updated datetime,
                hidden boolean
                );
                '''
            )
            await db.execute(
                r'''
                CREATE TABLE IF NOT EXISTS files ( 
                board text,
                thread integer,
                timestamp datetime,
                name text,
                path text,
                size integer,
                height integer,
                width integer,
                thumbnail text,
                thumbnail_height integer,
                thumbnail_width integer,
                md5 text
                );
                '''
            )
            await db.commit()
        logger.info('Database initialized')

    async def get_state(self, board, thread_ids=None):
        """Get current saved state for every thread in board."""
        sql = 'SELECT * FROM threads WHERE board = ?'
        if thread_ids is not None and len(thread_ids):
            sql = '{} AND id IN ({})'.format(
                sql, ','.join([str(t) for t in thread_ids])
            )
        state = {}
        async with self.get_db() as db:
            async with db.execute(sql, (board,)) as cursor:
                async for row in cursor:
                    state[row['id']] = row
        return state

    async def update_thread_state(self, board, thread, last_id):
        """Update thread in database after check."""
        thread_id = int(thread['num'])
        async with self.get_db() as db:
            # Check if thread exists
            query = 'SELECT id FROM threads WHERE id = ? AND board = ?'
            async with db.execute(query, (thread_id, board)) as cursor:
                res = await cursor.fetchone()

            if res:
                # Update thread
                sql = r'''
                UPDATE threads SET last = ?, updated = ?, files_count = ?
                WHERE id = ? AND board = ?
                '''
            else:
                # Insert thread
                sql = r'''
                INSERT INTO threads (last, updated, files_count, id, board)
                VALUES (?, ?, ?, ?, ?)
                '''

            args = (last_id, datetime.datetime.utcnow().timestamp(),
                    thread['files_count'], thread_id, board)
            await db.execute(sql, args)
            await db.commit()

    async def cleanup(self, board, thread_ids):
        """Remove old threads from database. We assuming that thread never
        appears in catalog once it is gone."""
        sql = 'DELETE FROM threads WHERE board = ? AND id NOT IN ({})'.format(
            ','.join([str(t) for t in thread_ids])
        )
        async with self.get_db() as db:
            await db.execute(sql, (board,))
            await db.commit()

    async def save_videos(self, files):
        """Insert new videos into database."""
        checksums = defaultdict(list)
        # Get already existing files with same md5 for same boards
        for f in files:
            checksums[f['board']] = f['md5']
        existing = set()
        async with self.get_db() as db:
            for board, md5_list in checksums.items():
                q = 'SELECT * FROM files WHERE board=? AND md5 IN ({})'.format(
                    ','.join(["'{}'".format(m) for m in md5_list])
                )
                async with db.execute(q, (board,)) as cursor:
                    async for row in cursor:
                        if row['md5'] in md5_list:
                            existing.add((board, row['md5']))
            for f in files:
                if (f['board'], f['md5']) in existing:
                    # Update existing file
                    sql = r'''
                    UPDATE files SET
                    name=?, path=?, size=?, height=?, width=?,
                    thumbnail=?, thumbnail_height=?, thumbnail_width=?,
                    timestamp=?, thread=?
                    WHERE board=? AND md5=?
                    '''
                    logger.debug('Updating file: board %s, checksum %s',
                                 f['board'], f['md5'])
                else:
                    # Insert new video
                    sql = r'''
                    INSERT INTO files (name, path, size, 
                    height, width, thumbnail, thumbnail_height,
                    thumbnail_width, timestamp, thread, board, md5)
                    VALUES (?, ?, ?, 
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?)
                    '''
                    logger.debug('Inserting file: board %s, checksum %s',
                                 f['board'], f['md5'])
                args = (f['name'], f['path'], f['size'],
                        f['height'], f['width'],
                        f['thumbnail'], f['tn_height'], f['tn_width'],
                        f['timestamp'], f['thread'],
                        f['board'], f['md5'])
                await db.execute(sql, args)
            await db.commit()

    async def get_videos(self):
        """Get list of videos with filter."""
        sql = 'SELECT * FROM files ORDER BY timestamp DESC LIMIT 50'
        videos = []
        async with self.get_db() as db:
            async with db.execute(sql) as cursor:
                async for row in cursor:
                    yield row
