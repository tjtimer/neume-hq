"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
import sys
from pprint import pprint
import ujson as json
import jinja2
import jinja2_sanic
from graphql.execution import ExecutionResult
from promise import Promise
from sanic.exceptions import NotFound

sys.path.append(__package__)

from aio_arango.client import ArangoAdmin
from aio_arango.db import ArangoDB
from graphql.execution.executors.asyncio import AsyncioExecutor
from sanic import Sanic, response
from sanic_graphql.graphqlview import GraphQLView

from neume_hq.api.schema import schema
from neume_hq.utilities import Config

STATIC_DIR = '/var/www/neume-hq/public/static'
grants = {'admin': 'rw', 'reader': 'ro'}

def gql_middleware(next, root, info, **kwargs):
    print('gql_middleware before: ', next)
    return_value = next(root, info, **kwargs)
    print('gql_middleware after: ', return_value)
    return return_value

def get_app():
    app = Sanic('NEUME-HQ')
    app.gq_schema = schema
    Config(app, '../conf')
    app.on_close = []
    app.static('/assets', f'{STATIC_DIR}/assets')
    app.static('/img', f'{STATIC_DIR}/img')
    app.static('/js', f'{STATIC_DIR}/js')

    app.static(
        '/service-worker.js',
        f'{STATIC_DIR}/service-worker.js')

    loader = jinja2.FileSystemLoader(searchpath=['/var/www/neume-hq/public'])
    jinja2_sanic.setup(app, loader=loader)
    app.render = jinja2_sanic.render_template


    @app.middleware('request')
    def request_mw(request):
        print('before')
        request.app.gq_db.count = 0
        print(request.app.gq_db.count)

    @app.middleware('response')
    def response_mw(request, response):
        print('after')
        print(request.app.gq_db.count)

    @app.get('/')
    async def index(request):
        return app.render('index.html', request, {})

    async def not_found(request, *_):
        if request.headers.get('referer', None) is None:
            return await index(request)
        return response.raw(b'\x00')

    app.error_handler.add(NotFound, not_found)

    @app.listener('before_server_start')
    async def setup(app, loop):
        app._executor = AsyncioExecutor(loop=loop)
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

        app.gq_db = ArangoDB('user', 'user-pw', 'public')
        await app.gq_db.login()
        app.add_route(
            GraphQLView.as_view(
                schema=await schema.setup(app.gq_db),
                context={'db': app.gq_db, 'cache': {}},
                batch=True,
                executor=app._executor,
                graphiql=True
            ), 'graphql'
        )


    @app.listener('after_server_stop')
    async def close(app, loop):
        await asyncio.gather(*(
            func() for func in app.on_close
        ))
        await app.gq_db.close()
        print('server closed')

    return app

app = get_app()

if __name__ == '__main__':
    app.run(port=7666, debug=True)
