"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from uuid import UUID

import arrow
from graphene import Scalar, Int, String, List, ObjectType, Dynamic, Field
from graphene.types.structures import Structure
from graphql.execution.tests.test_lists import ast


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
        print('Email coercing value: ', value)
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
        print('Password coercing value: ', value)
        return value

    serialize = coerce_string
    parse_value = coerce_string

    @staticmethod
    def parse_literal(ast):
        print('Password parsing literal: ', ast)
        if isinstance(ast, ast.StringValue):
            return ast.value


class GQField(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None):
        self.class_name = class_name
        self._cls = None
        self.query = query
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        def get_dynamic():
            from .gql import registry
            self._cls = registry[self.class_name]
            return Field(self._cls,
                        first=Int(), skip=Int(), search=String(),
                        resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolve(self,
                        inst, info,
                        first: Int = None, skip: Int = None,
                        search: String = None):
        self.query.start_vertex, db = inst._id, info.context['db']
        result = await db.fetch_one(self.query.statement)
        return self._cls(**result[0]) if len(result) else 'none'


class GQList(Dynamic):

    def __init__(self, class_name: str, query=None, resolver=None):
        self.class_name = class_name
        self._cls = None
        self.query = query
        if resolver is None:
            resolver = self.__resolve
        self.__resolver = resolver
        def get_dynamic():
            from .gql import registry
            self._cls = registry[self.class_name]
            return List(self._cls,
                        first=Int(), skip=Int(), search=String(),
                        resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolve(self,
                        inst, info,
                        first: Int = None, skip: Int = None,
                        search: String = None):
        self.query.start_vertex, db = inst._id, info.context['db']
        return [self._cls(**obj)
                async for obj in db.query(self.query.statement)
                if obj is not None]

