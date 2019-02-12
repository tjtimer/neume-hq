"""
test_queries
author: Tim "tjtimer" Jedro
created: 04.02.19
"""
import random
from pprint import pprint

async def test_query_people(test_cli, url_builder):
    resp = await test_cli.post(
        url_builder(query=('query {'
                           '  people { Id, name, email }'
                           '}')))
    assert resp.status == 200
    data = await resp.json()
    assert 'data' in data.keys()
    assert 'people' in data['data'].keys()
    assert isinstance(data['data']['people'], list)
    for person in data['data']['people']:
        assert all(map(lambda k: k in person.keys(), ['Id', 'name', 'email']))


async def test_create_person(test_cli, url_builder, dumps, user_data):
    for data in user_data:
        # if data['birthday'] is None:
        #     query = ('mutation '
        #              'personCreation('
        #              '  $name: String, '
        #              '  $email: Email'
        #              ') {'
        #              '  createPerson('
        #              '    name: $name, '
        #              '    email: $email'
        #              '  )'
        #              ' { Id, name, email, Created }'
        #              '}')
        #     data.pop('birthday', None)
        # else:
        query = ('mutation '
                 'personCreation('
                 '  $person: PersonInput, '
                 ') {'
                 '  createPerson('
                 '    person: $person, '
                 '  )'
                 ' { Id, name, email, Created }'
                 '}')
        resp = await test_cli.post(
            url_builder(
                query=query,
                variables=dumps({'person': data})
            )
        )
        # assert resp.status == 200
        data = await resp.json()
        assert 'data' in data.keys()
        pprint(data)

async def test_create_friends(people_ids, test_cli, url_builder, dumps):
    inp_data = {}
    ids = [_id async for _id in people_ids()]
    query = ('mutation '
             'createFriendship($knows: KnowsInput) {'
             '  createKnows(knows: $knows)'
             '  {Id}'
             '}')
    while True:
        if len(ids) <= 2:
            break
        inp_data['From'] = ids.pop(0)
        count = min(random.randint(0, len(ids)-2), 10)
        possible_ids = [*ids]
        max_idx = len(possible_ids) - 1
        for i in range(count):
            inp_data['To'] = possible_ids.pop(random.randint(0, max_idx-i))
            resp = await test_cli.post(
                url_builder(
                    query=query,
                    variables=dumps({'knows': inp_data})
                )
            )
            # assert resp.status == 200
            data = await resp.json()
            assert 'data' in data.keys()
