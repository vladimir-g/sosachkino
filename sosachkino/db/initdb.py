import logging
import logging.config
import argparse
import configparser
from sqlalchemy import create_engine
from sqlalchemy.engine import url
from sqlalchemy.dialects import postgresql

from sosachkino.db.base import Base, Meta
from sosachkino.db.models import *


def initdb():
    """Recreate database tables."""
    parser = argparse.ArgumentParser(
        description='Initialize sosachkino database (warning: existing tables will be dropped).'
    )
    parser.add_argument('--config', required=True,
                        help='path to config ini file')
    args = parser.parse_args()

    logging.config.fileConfig(args.config)
    logger = logging.getLogger(__name__)
    logger.info('Loading config file')

    config = configparser.ConfigParser()
    config.read(args.config)

    # An hack
    conf = config['db']
    conf['username'] = config['db']['user']
    del conf['user']

    logger.info('Creating engine')
    engine = create_engine(url.URL(drivername='postgres', **config['db']))

    logger.info('Dropping all tables')
    Meta.drop_all(engine)
    logger.info('Creating tables')
    Meta.create_all(engine)
    logger.info('Finished')


def print_sql():
    parser = argparse.ArgumentParser(
        description='Print SQL statements for database creation.'
    )
    parser.add_argument('--config', required=True,
                        help='path to config ini file')
    args = parser.parse_args()

    logging.config.fileConfig(args.config)
    logger = logging.getLogger(__name__)
    logger.info('Loading config file')

    config = configparser.ConfigParser()
    config.read(args.config)

    # An hack
    conf = config['db']
    conf['username'] = config['db']['user']
    del conf['user']

    def metadata_dump(sql, *multiparams, **params):
        print(sql.compile(dialect=postgresql.dialect()))

    engine = create_engine(url.URL(drivername='postgres', **config['db']),
                           strategy='mock', executor=metadata_dump)
    Meta.create_all(engine)
