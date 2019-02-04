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
            dt = arrow.get(value).date()
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
            return arrow.get(value).date()
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
            return arrow.get(value)
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

def get_or_create_type(field, include=None):
    from .gql import registry
    if include is None:
        cls = registry[field.class_name]
    elif include[0] in registry.keys():
        cls = registry[include[0]]
    else:
        cls = type(
            include[0],
            (registry[field.class_name], ObjectType),
            {**include[1]}
        )
        registry[include[0]] = cls
    return cls

class GQField(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None, include=None):
        self.class_name = class_name
        self._cls = None
        self._query = query
        if query is not None:
            self._query.f('v._id').like(f'{ifl.plural(snake_case(class_name))}%')
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        self._include = include

        def get_dynamic():
            self._cls = get_or_create_type(self, include)
            return Field(self._cls,
                        first=Int(), skip=Int(), search=String(),
                        resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolve(self,
                        inst, info,
                        first: Int = None, skip: Int = None,
                        search: String = None):
        db = info.context['db']
        self._query.start_vertex = inst._id
        result = await db.fetch_one(self._query.statement)
        return self._cls(**result[0]) if len(result) else None


class GQList(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None, include=None):
        self.class_name = class_name
        self._cls = None
        self._query = query
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        self._include = include

        def get_dynamic():
            self._cls = get_or_create_type(self, include)
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

