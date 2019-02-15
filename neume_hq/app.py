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

grants = {'admin': 'rw', 'reader': 'ro'}

def gql_middleware(next, root, info, **kwargs):
    print('gql_middleware before: ', next)
    return_value = next(root, info, **kwargs)
    print('gql_middleware after: ', return_value)
    return return_value

def get_app():
    app = Sanic('NEUME-HQ')
    Config(app, '../conf')
    app.on_close = []
    app.static('/assets', '/var/www/neume-hq/public/static/assets')
    app.static('/img', '/var/www/neume-hq/public/static/img')
    app.static('/js', '/var/www/neume-hq/public/static/js')

    app.static(
        '/service-worker.js',
        '/var/www/neume-hq/public/static/assets/service-worker.js')

    loader = jinja2.FileSystemLoader(searchpath=['/var/www/neume-hq/public'])
    jinja2_sanic.setup(app, loader=loader)
    app.render = jinja2_sanic.render_template

    @app.post('/graphql')
    async def gql_mw(request):
        query = request.json.get('query', None)
        if query is not None:
            request.app.gq_db.count = 0
            qu = query
            pprint(qu)
            try:
                _res = request.app.gq_schema._schema.execute(query)
                pprint(_res)
                result = _res
                pprint(result)
                return response.json(result)
            except Exception as e:
                return response.text(e)

    @app.middleware('response')
    def mw(request, response):
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

        app.gq_db = db = ArangoDB('user', 'user-pw', 'public')
        await db.login()
        app.gq_schema = schema
        app.add_route(
            GraphQLView.as_view(
                schema=await schema.setup(db),
                context={'db': db},
                batch=True,
                executor=app._executor,
                graphiql=False
            ), 'graphql2'
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
