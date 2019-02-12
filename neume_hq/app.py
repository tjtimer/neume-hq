"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
import sys

import jinja2
import jinja2_sanic

sys.path.append(__package__)

from aio_arango.client import ArangoAdmin
from aio_arango.db import ArangoDB
from graphql.execution.executors.asyncio import AsyncioExecutor
from sanic import Sanic
from sanic_graphql.graphqlview import GraphQLView

from neume_hq.api.schema import schema
from neume_hq.utilities import Config

grants = {'admin': 'rw', 'reader': 'ro'}

def get_app():
    app = Sanic('NEUME-HQ')
    Config(app, '../conf')
    app.on_close = []

    app.static('static/', '/var/www/neume-hq/public/static/')
    app.static('/*.js', '/var/www/neume-hq/public/assets/*.js', content_type='text/*')
    app.static(
        '/service-worker.js',
        '/var/www/neume-hq/public/assets/service-worker.js',
        content_type='text/javascript')

    loader = jinja2.FileSystemLoader(searchpath=['/var/www/neume-hq/public'])
    jinja2_sanic.setup(app, loader=loader)
    app.render = jinja2_sanic.render_template


    @app.get('/')
    async def index(request):
        ctx = {}
        return app.render('index.html', request, ctx)

    @app.listener('before_server_start')
    async def setup(app, loop):
        async with ArangoAdmin('root', 'arango-pw') as admin:
            dbs, users = await asyncio.gather(
                admin.get_dbs(),
                admin.get_users()
            )
            await asyncio.gather(
                    *(admin.create_user(name, pw)
                      for name, pw in app.config.DB_USERS.items()
                      if name not in [usr['user'] for usr in users])
                )
            for db_name, cfg in app.config.DATABASES.items():
                if db_name not in dbs:
                    await admin.create_db(db_name)
                await asyncio.gather(
                    *(admin.set_access_level(name,
                                             db_name,
                                             level=grants[role])
                      for role, name in cfg['users'].items()),
                    *(admin.set_access_level(name,
                                             db_name,
                                             level='none')
                      for name in app.config.DB_USERS.keys()
                      if name not in cfg['users'].values())
                )

        db = ArangoDB('user', 'user-pw', 'public')
        await db.login()
        app_schema = await schema.setup(db)
        app.add_route(
            GraphQLView.as_view(
                schema=app_schema,
                context={'db': db, 'schema': app_schema},
                executor=AsyncioExecutor(loop=loop),
                graphiql=True
            ), 'graphql'
        )
        app.on_close.append(db.close)


    @app.listener('after_server_stop')
    async def close(app, loop):
        await asyncio.gather(*(
            func() for func in app.on_close
        ))
        print('server closed')

    return app

app = get_app()

if __name__ == '__main__':
    app.run(port=7666, debug=True)
