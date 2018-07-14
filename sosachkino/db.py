import logging
import datetime
import aiosqlite


logger = logging.getLogger(__name__)


class DB:
    """Wrapper for sqlite database."""
    def __init__(self, path):
        self.path = path

    async def init(self):
        """Init database connection and create tables."""
        logger.info('Initializing database at %s', self.path)
        self.conn = aiosqlite.connect(self.path)
        cursor = await self.conn.execute(
            r'''
            CREATE TABLE IF NOT EXISTS threads ( 
            id integer PRIMARY KEY,
            board text,
            last integer,
            updated datetime,
            hidden boolean
            );
            '''
        )
        cursor = await db.execute(
            r'''
            CREATE TABLE IF NOT EXISTS files ( 
            id integer PRIMARY KEY,
            thread integer,
            created datetime,
            );
            '''
        )
        await self.conn.commit()
        logger.info('Database initialized')

    async def close(self):
        await self.conn.close()
