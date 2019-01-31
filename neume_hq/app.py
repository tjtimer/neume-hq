"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
from pprint import pprint

from aio_arango.client import ArangoAdmin
from aio_arango.db import ArangoDB
from graphql.execution.executors.asyncio import AsyncioExecutor
from sanic import Sanic
from sanic_graphql.graphqlview import GraphQLView

from neume_hq.pub_api.schema import schema
from neume_hq.utilities import Config

app = Sanic('NEUME-HQ')
app.on_close = []

Config(app, '../conf')

grants = {'admin': 'rw', 'reader': 'ro'}

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
    app.add_route(
        GraphQLView.as_view(
            schema=await schema.setup(db),
            context={'db': db, 'schema': schema},
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


if __name__ == '__main__':
    app.run(port=7666, debug=True)
