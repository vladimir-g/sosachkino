import argparse
import configparser
import logging
import logging.config
import pathlib

from sosachkino.api import Api
from sosachkino.db import DB
from sosachkino.updater import Updater

import asyncio

logger = logging.getLogger(__name__)


async def run():

    parser = argparse.ArgumentParser(
        description='Web-based sosach webm viewer.'
    )
    parser.add_argument('--config', default=pathlib.Path.cwd() / 'config.ini',
                        help='config file (default: ./config.ini)')
    args = parser.parse_args()

    # Initialize logging
    logging.config.fileConfig(args.config)

    # Initialize config
    config = configparser.ConfigParser()
    config.read(args.config)

    api = Api()
    db = DB(config['db']['path'])
    await api.init()
    await db.init()

    updater = Updater(api, db)
    await updater.update()

    await api.close()
    await db.close()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())
