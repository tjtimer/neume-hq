"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from pprint import pprint
import ujson as json
from graphene import ObjectType, String, Scalar

from neume_hq.gql.fields import DateTime, GQList, GQField
from neume_hq.utilities import ifl, snake_case

node_registry = {}
edge_registry = {}

class Index:
    def __init__(self, *fields: list or tuple,
                 type: str = None, unique: bool = None, sparse: bool = None):
        self.fields = fields
        self.type = 'hash' if type is None else type
        self.unique = True if unique is None else unique
        self.sparse = False if sparse is None else sparse


class BaseModel(ObjectType):

    def __init_subclass__(cls, **kwargs):
        for k, v in cls.__dict__.items():
            if isinstance(v, (GQField, GQList)):
                v.parent_name = cls.__name__
                v.field_name = k
        cls._config_ = {}
        if hasattr(cls, 'Config'):
            cls._config_.update(**cls.Config.__dict__)
            delattr(cls, 'Config')

        cls.id = String()
        cls._id = String()
        cls._key = String()
        cls._rev = String()
        cls._created = DateTime()
        cls._updated = DateTime()

        super().__init_subclass__(**kwargs)

    @property
    def indexes(self):
        return self._config_.get('indexes', [])

    @property
    def _state(self) -> dict:
        return {k: v
                for k, v in self.__dict__.items()
                if v is not None and isinstance(v, Scalar)}

    def resolve_id(self, *_):
        return self._key if self._key else str(self._id).split('/')[-1]

    @classmethod
    async def find(cls, info, id=None):
        print(f'find {cls.__name__} with id: {id}')
        pprint(info.context['request'].json)
        resp = await info.context['db'][cls._collname_].get(id)
        return cls(**await resp.json())

    @classmethod
    async def all(cls, _, info, id=None, filter: dict=None):
        print(f'all {cls._collname_}')
        pprint(info.context['request'].json)
        resp = await info.context['db'][cls._collname_].all()
        return (cls(**obj) for obj in resp)

class Node(BaseModel):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._collname_ = ifl.plural(snake_case(cls.__name__))
        node_registry[cls.__name__] = cls


class Edge(BaseModel):

    def __init_subclass__(cls, **kwargs):
        cls._from = String()
        cls._to = String()
        super().__init_subclass__(**kwargs)
        cls._collname_ = snake_case(cls.__name__)
        edge_registry[cls.__name__] = cls


