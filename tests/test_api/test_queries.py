"""
test_queries
author: Tim "tjtimer" Jedro
created: 04.02.19
"""
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
                 '  $name: String, '
                 '  $email: Email, '
                 '  $birthday: Date'
                 ') {'
                 '  createPerson('
                 '    name: $name, '
                 '    email: $email, '
                 '    birthday: $birthday'
                 '  )'
                 ' { Id, name, email, Created }'
                 '}')

        pprint(data)
        resp = await test_cli.post(
            url_builder(
                query=query,
                variables=dumps(data)
            )
        )
        # assert resp.status == 200
        data = await resp.json()
        assert 'data' in data.keys()
        pprint(data)
