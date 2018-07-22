import logging
import logging.config
import argparse
import configparser
from sqlalchemy import create_engine

from sosachkino.db import Base, Meta
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

    logger.info('Creating engine')
    conn_string = config['db']['conn_string']
    engine = create_engine(conn_string)

    logger.info('Dropping all tables')
    Meta.drop_all(engine)
    logger.info('Creating tables')
    Meta.create_all(engine)
    logger.info('Finished')
