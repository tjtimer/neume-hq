"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from uuid import UUID

import arrow
from graphene import Dynamic, Field, Int, List, ObjectType, Scalar, String
from graphql.execution.tests.test_lists import ast

from neume_hq.utilities import ifl, snake_case


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


class ID(Scalar):

    @staticmethod
    def serialize(value):
        try:
            return UUID(value).hex
        except ValueError:
            return None

    @classmethod
    def parse_literal(cls, node):
        if isinstance(node, ast.StringValue):
            return cls.parse_value(node.value)

    @staticmethod
    def parse_value(value):
        try:
            return UUID(value)
        except ValueError:
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

def get_or_create_type(field, extra=None):
    from .gql import registry
    if extra is None:
        return registry[field.class_name]
    try:
        field_name = ifl.singular_noun(field.field_name).title()
    except AttributeError:
        field_name = field.field_name.title()
    name = f'{field.parent_name}{field_name}'
    if name in registry.keys():
        return registry[name]
    registry[name] = type(
        name,
        (registry[field.class_name], ObjectType),
        {**extra}
    )
    return registry[name]

class GQField(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None, extra=None):
        self._cls = None
        self._query = query
        if query is not None:
            self._query.f('v._id').like(f'{ifl.plural(snake_case(class_name))}%')
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        self._extra = extra

        self.class_name = class_name
        self.parent_name = None
        self.field_name = None

        def get_dynamic():
            self._cls = get_or_create_type(self, extra)
            return Field(self._cls, resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolve(self, inst, info):
        db = info.context['db']
        self._query.start_vertex = inst._id
        result = await db.fetch_one(self._query.statement)
        return self._cls(**result[0]) if len(result) else None


class GQList(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None, extra=None):
        self._cls = None
        self._query = query
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        self._extra = extra

        self.class_name = class_name
        self.parent_name = None
        self.field_name = None

        def get_dynamic():
            print('GQList get_dynamic: ', self.class_name)
            self._cls = get_or_create_type(self, extra)
            return List(self._cls,
                        first=Int(), skip=Int(), search=String(),
                        resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolve(self,
                        inst, info,
                        first: Int = None, skip: Int = None,
                        search: String = None):
        self._query.start_vertex, db = inst._id, info.context['db']
        return [self._cls(**obj)
                async for obj in db.query(self._query.statement)
                if obj is not None]

