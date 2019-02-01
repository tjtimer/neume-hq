"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from collections import ChainMap
from pprint import pprint

import arrow as arrow
from aio_arango.client import ClientError
from graphene import String, Interface, ObjectType

from neume_hq.gql.fields import ID, DateTime
from neume_hq.utilities import ifl, snake_case

registry = {'node': {}, 'edge': {}}

class Index:
    def __init__(self, *fields: list or tuple,
                 type: str = None, unique: bool = None, sparse: bool = None):
        self.fields = fields
        self.type = 'hash' if type is None else type
        self.unique = True if unique is None else unique
        self.sparse = False if sparse is None else sparse


class BaseModel(ObjectType):

    def __init_subclass__(cls, **kwargs):
        cls._collname_ = snake_case(cls.__name__)
        cls._config_ = {}
        if hasattr(cls, 'Config'):
            cls._config_.update(**cls.Config.__dict__)
            delattr(cls, 'Config')

        cls._id = ID()
        cls._key = String()
        cls._rev = String()
        cls._created = DateTime()
        cls._updated = DateTime()

        super().__init_subclass__(**kwargs)

    @property
    def id(self):
        return self._key if self._key else str(self._id).split('/')[-1]

    @property
    def indexes(self):
        return self._config_.get('indexes', [])

    @property
    def _state(self) -> dict:
        return {k: v
                for k, v in self.__dict__.items()
                if k in ['_from', '_to'] or
                not k.startswith('_') and v is not None}

    async def create(self, client):
        obj = await client[self._collname_].add(
            {**self._state, '_created': arrow.utcnow().timestamp},
            params={'returnNew': 'true'}
        )
        self.__dict__.update(**obj['new'])

    async def get(self, client):
        obj = await client[self._collname_].get(self.id)
        self.__dict__.update(**obj)

    async def update(self, client):
        no_id = self.id in (None, '')
        if no_id:
            raise ClientError(
                f'Can not update instance of {self.__class__.__name__}. '
                f'Attribute _id must be given.'
            )
        obj = await client[self._collname_].update(
            self.id,
            {**self._state, '_updated': arrow.utcnow().timestamp},
            params={'returnNew': 'true'}
        )
        self.__dict__.update(**obj['new'])

class Node(BaseModel):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._collname_ = ifl.plural(snake_case(cls.__name__))

class Edge(BaseModel):

    def __init_subclass__(cls, **kwargs):
        cls._from = String()
        cls._to = String()
        super().__init_subclass__(**kwargs)


