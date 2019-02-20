"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from pprint import pprint

from graphene import Connection, ObjectType, Scalar, String, relay, ID

from neume_hq.gql.fields import DateTime, GQField, GQList
from neume_hq.utilities import ifl, pascal_case, snake_case

node_registry = {}
edge_registry = {}
connection_registry = {}

__cache = {}

class Index:
    def __init__(self, *fields: list or tuple,
                 type: str = None, unique: bool = None, sparse: bool = None):
        self.fields = fields
        self.type = 'hash' if type is None else type
        self.unique = True if unique is None else unique
        self.sparse = False if sparse is None else sparse

class ModelConfig:
    def __init__(self):
        self.indexes = ()
        self.relations = {}

    def update(self, **cfg):
        self.indexes = (*self.indexes, *cfg.pop('indexes', ()))
        self.relations.update(
            **cfg.pop('relations', {}),
            **{'_from': cfg.pop('_from', ()),
               '_to': cfg.pop('_to', ()),
               '_any': cfg.pop('_any', ())}
        )


class BaseModel(ObjectType):
    def __init_subclass__(cls, **kwargs):
        cls._config_ = ModelConfig()
        for k, v in {**cls.__dict__}.items():
            if isinstance(v, (GQField, GQList)):
                v.parent_name = cls.__name__
                v.field_name = k

        if hasattr(cls, 'Config'):
            cls._config_.update(**cls.Config.__dict__)
            delattr(cls, 'Config')

        cls._id = String()
        cls._key = String()
        cls._rev = String()
        cls._created = DateTime()
        cls._updated = DateTime()

        super().__init_subclass__()

    @property
    def indexes(self):
        return self._config_.indexes

    @property
    def relations(self):
        return self._config_.relations

    @property
    def _state(self) -> dict:
        return {k: v
                for k, v in self.__dict__.items()
                if isinstance(v, Scalar)}

    def resolve_id(self, *_):
        return self._id

    @classmethod
    async def find(cls, _, info, **kwargs):
        print('find: ', cls)
        _key = kwargs.pop('id', kwargs.pop('_id', '')).split('/')[-1]
        resp = await info.context['db'][cls._collname_].get(_key)
        return cls(**resp)

    @classmethod
    async def all(cls, _, info, **kwargs):
        print('model all ', cls)
        #
        # sets = [(0, f.name.value, f.selection_set) for f in info.field_asts]
        # pprint(sets)
        # cls_name = ''
        # queries = {}
        # while True:
        #     if len(sets) <= 0:
        #         break
        #     depth, name, sel_set = sets.pop(0)
        #     if sel_set is not None:
        #         if name not in ['node', 'edges']:
        #             cls_name = f'{depth}-{name}'
        #             queries[cls_name] = set()
        #             depth += 1
        #         sets.extend([
        #             (depth, f.name.value, f.selection_set)
        #             for f in sel_set.selections])
        #     else:
        #         queries[cls_name].add(name)
        # pprint(queries)
        resp = await info.context['db'][cls._collname_].all()
        return [cls(**obj) for obj in resp]

class GQNode(relay.Node):
    class Meta:
        name = 'Node'

    @classmethod
    async def to_global_id(cls, type, id):
        return id

    @classmethod
    async def get_node_from_global_id(cls, info, global_id, only_type=None):
        print('get from gid ', global_id)
        type, id = global_id.split('/')
        if only_type:
            # We assure that the node type that we want to retrieve
            # is the same that was indicated in the field type
            assert type == only_type._meta.name, 'Received not compatible node.'
        model = node_registry[ifl.singular_noun(pascal_case(type))]
        return await model.get_node(info, id)


class Node(BaseModel):

    def __init_subclass__(cls, **kwargs):
        cls.Meta = type('Meta', (), {'interfaces': (GQNode,)})
        super().__init_subclass__(**kwargs)
        cls._collname_ = ifl.plural(snake_case(cls.__name__))
        node_registry[cls.__name__] = cls
        connection_registry[cls._collname_] = type(
            f'{cls.__name__}Connection',
            (Connection,),
            {'Meta': type('Meta', (), {'node': cls})}
        )

    @classmethod
    async def get_node(cls, info, id):
        print('get node called', cls, id)
        return await cls.find(None, info, id=id)

class Edge(BaseModel):

    def __init_subclass__(cls, **kwargs):
        cls._from = String()
        cls._to = String()
        super().__init_subclass__(**kwargs)
        cls._collname_ = snake_case(cls.__name__)
        edge_registry[cls.__name__] = cls


