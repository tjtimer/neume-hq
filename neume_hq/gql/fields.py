"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""

import arrow
from graphene import Connection, Dynamic, Scalar, String, relay, Field
from graphql.execution.tests.test_lists import ast

from neume_hq.utilities import ifl, pascal_case, snake_case


class Date(Scalar):

    @staticmethod
    def serialize(value):
        try:
            dt = arrow.get(value)
            return dt.format('YYYY-MM-DD')
        except TypeError:
            return None

    @classmethod
    def parse_literal(cls, node):
        return cls.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        try:
            v = arrow.get(value).format('YYYY-MM-DD')
            print('parse date: ', v)
            return v
        except TypeError:
            return None


class Time(Scalar):

    @staticmethod
    def serialize(value):
        try:
            dt = arrow.get(value).time()
            return dt.for_json()
        except TypeError:
            return None

    @classmethod
    def parse_literal(cls, node):
        if isinstance(node, ast.StringValue):
            return cls.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        try:
            return arrow.get(value).time()
        except TypeError:
            return None


class DateTime(Scalar):

    @staticmethod
    def serialize(value):
        try:
            dt = arrow.get(value)
            return dt.for_json()
        except TypeError:
            return None

    @classmethod
    def parse_literal(cls, node):
        if isinstance(node, ast.StringValue):
            return cls.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        try:
            v = arrow.get(value).timestamp
            print('parse datetime: ', v)
            return v
        except TypeError:
            return None


class Email(String):
    """
    The `String` scalar type represents textual data, represented as UTF-8
    character sequences. The String type is most often used by GraphQL to
    represent free-form human-readable text.
    """

    @staticmethod
    def coerce_string(value):
        return value

    serialize = coerce_string
    parse_value = coerce_string


class Password(Scalar):
    """
    The `String` scalar type represents textual data, represented as UTF-8
    character sequences. The String type is most often used by GraphQL to
    represent free-form human-readable text.
    """

    @staticmethod
    def coerce_string(value):
        return value

    serialize = coerce_string
    parse_value = coerce_string

    @staticmethod
    def parse_literal(ast):
        if isinstance(ast, ast.StringValue):
            return ast.value


connection_registry = {}

class GQField(Dynamic):

    _is_list = False

    def __init__(self, node_type: str, query, extra: dict=None):

        self._cls = None
        query.f('v._id').like(f'{ifl.plural(snake_case(node_type))}/%')
        self._query = query
        self._extra = {
            'pId': String()}
        if isinstance(extra, dict):
            self._extra.update(**extra)

        self.node_type_name = node_type
        self.node_type = None
        self.parent_name = None
        self.field_name = None

        def get_dynamic():
            cls = self.create_type()
            if self._is_list is False:
                return Field(lambda: self.node_type, resolver=self.resolve)
            return relay.ConnectionField(cls, resolver=self.resolve)
        super().__init__(get_dynamic)

    def create_type(self):
        from .gql import registry
        self._is_list = True
        self.node_type = registry[self.node_type_name]
        field_name = ifl.singular_noun(self.field_name)
        if field_name is False:
            self._is_list = False
            field_name = self.field_name
        name = f'{self.parent_name}{pascal_case(field_name)}'
        # if self.node_type is None:
        #     from neume_hq.gql.models import GQNode
        #     self.node_type = registry[name] = type(
        #         name,
        #         (registry[self.node_type_name], ObjectType),
        #         {
        #             'Meta': type('Meta', (), {'interfaces': (GQNode,)}),
        #             'Edge': type('Edge', (), self._extra)}
        #     )
        conn_name = f'{name}Connection'
        self._cls = connection_registry.get(conn_name, None)
        if  self._cls is None:
            self._cls = connection_registry[conn_name] = type(
                conn_name,
                (Connection,),
                {'Meta': type('Meta', (), {'node': self.node_type}),
                 'Edge': type('Edge', (), self._extra)}
            )
        return self._cls

    async def resolve(self, inst, info, id=None):
        self._query.start_vertex = inst._id
        data = {'_id': 'none'}
        obj = await info.context['db'].fetch_one(self._query.statement)
        data.update(**obj)
        return self.node_type(**data)


class GQList(GQField):
    _is_list = True
    async def resolve(self,
                      inst, info,
                      **kwargs):
        self._query.start_vertex, db = inst._id, info.context['db']
        edges = [obj async for obj in db.query(self._query.statement)
                if obj is not None]
        return self._cls(edges=[
            self._cls.Edge(
                **{k: v for k, v in obj.items() if k!= 'node'},
                node=self.node_type(**obj['node'])
            ) for obj in edges
        ])
