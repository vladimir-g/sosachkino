import argparse
import configparser
import logging
import logging.config
import pathlib
import aiohttp_jinja2
import jinja2
from aiohttp import web

from sosachkino.api import Api
from sosachkino.db import DB
from sosachkino.updater import Updater
from sosachkino.views.videos import VideosView


logger = logging.getLogger(__name__)
logging.getLogger('asyncio').setLevel(logging.DEBUG)

def main():
    """Init all objects and start aiohttp web server."""
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

    logger.info('Initializing application')
    app = web.Application()
    app['config'] = config

    jinja_env = aiohttp_jinja2.setup(
        app, loader=jinja2.PackageLoader('sosachkino', 'templates')
    )

    # API wrapper
    api = Api()
    app['api'] = api

    # Database
    db = DB(config['db'])
    app['db'] = db

    # Updater
    updater = Updater(config, api, db)
    app['updater'] = updater

    # Init api and database
    app.on_startup.append(db.init)
    app.on_startup.append(api.init)
    app.on_startup.append(updater.start_task)

    # Close them on finish
    app.on_cleanup.append(api.close)
    app.on_cleanup.append(db.shutdown)
    app.on_cleanup.append(updater.cleanup_task)

    # Routing and views
    videos = VideosView(app)

    app.add_routes([
        web.get('/', videos.list, name='videos')
    ])

    app.router.add_static('/static/',
                          path=pathlib.Path(__file__).parent / 'static',
                          name='static')

    # Start server
    host = config['app'].get('host', 'localhost')
    port = int(config['app'].get('port', 8080))
    logger.info('Starting app on %s:%s', host, port)
    web.run_app(app, host=host, port=port)


if __name__ == '__main__':
    main()
