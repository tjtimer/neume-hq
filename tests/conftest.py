"""
conftest
author: Tim "tjtimer" Jedro
created: 04.02.19
"""
import re
import string
from urllib.parse import urlencode

import arrow
from aio_arango.db import ArangoDB
from hypothesis import strategies as st
import ujson as json

import pytest
from sanic.websocket import WebSocketProtocol

from neume_hq.app import get_app

@pytest.yield_fixture
def app():
    app = get_app()
    yield app


@pytest.fixture
def test_cli(loop, app, test_client):
    return loop.run_until_complete(
        test_client(
            app,
            protocol=WebSocketProtocol
        )
    )


@pytest.fixture
def base_url():
    return '/graphql'

@pytest.fixture
def url_builder(base_url):
    def builder(**url_params):
        if url_params:
            return '{}?{}'.format(base_url, urlencode(url_params))
        return base_url
    return builder

@pytest.fixture
def dumps():
    return json.dumps


# Example Data Object
# GoalData = st.fixed_dictionaries({
#     'title': st.text(),
#     'goal_type': st.sampled_from([
#         "hustler", "biker", "gainer", "fatloser", "inboxer",
#         "drinker", "custom"]),
#     'goaldate': st.one_of(st.none(), st.floats()),
#     'goalval': st.one_of(st.none(), st.floats()),
#     'rate': st.one_of(st.none(), st.floats()),
#     'initval': st.floats(),
#     'panic': st.floats(),
#     'secret': st.booleans(),
#     'datapublic': st.booleans(),
# })

PersonData = st.fixed_dictionaries({
    'name': st.text(alphabet=[*string.ascii_letters], min_size=3, max_size=25),
    'email': st.emails(),
    'birthday': st.one_of(st.none(), st.dates().map(lambda x: arrow.get(x).for_json()))
})

@pytest.fixture
def user_data():
    return (PersonData.example() for _ in range(10))

@pytest.fixture
async def people_ids(loop):
    async def _get_ids():
        async with ArangoDB('user', 'user-pw', 'public') as client:
            async for _id in client.query('FOR v in people RETURN v._id'):
                yield _id
    return _get_ids
