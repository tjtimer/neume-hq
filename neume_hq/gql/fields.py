"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from pprint import pprint
from typing import Optional
import ujson as json
from uuid import UUID

import arrow
from graphene import Dynamic, Field, List, ObjectType, Scalar, String
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
    if extra is None and isinstance(field.root_types, str):
        return registry[field.root_types]
    field_name = ifl.singular_noun(field.field_name)
    if field_name is False:
        field_name = field.field_name
    name = f'{field.parent_name}{field_name.title()}'
    if registry.get(name, None) is None:
        bases = []
        if isinstance(field.root_types, str):
            bases.append(registry[field.root_types])
        elif isinstance(field.root_types, list):
            bases.extend([registry[rt] for rt in field.root_types])
        registry[name] = type(
            name,
            (*bases, ObjectType),
            {**extra} or {}
        )
    return registry[name]

class GQField(Dynamic):

    def __init__(self, root_types: [list, str], query, extra: dict=None):
        self._cls = None
        if isinstance(root_types, str):
            query.f('v._id').like(f'{ifl.plural(snake_case(root_types))}/%')
        self._query = query
        self._extra = extra

        self.root_types = root_types
        self.parent_name = None
        self.field_name = None

        def get_dynamic():
            self._cls = get_or_create_type(self, extra)
            return Field(self._cls, resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolver(self, inst, info):
        db = info.context['db']
        self._query.start_vertex = inst._id
        pprint(self._query.statement)
        result = await db.fetch_one(self._query.statement)
        return self._cls(**result[0]) if len(result) else None


class GQList(Dynamic):

    def __init__(self, root_types: [str, list], query, extra=None):
        self._cls = None
        self._query = query
        self._extra = extra

        self.root_types = root_types
        self.parent_name = None
        self.field_name = None

        def get_dynamic():
            print('GQList get_dynamic: ', self.root_types)
            self._cls = get_or_create_type(self, extra)
            return List(self._cls,
                        resolver=self.__resolver)
        super().__init__(get_dynamic)

    async def __resolver(self,
                        inst, info,
                        filter: dict=None):
        self._query.start_vertex, db = inst._id, info.context['db']
        pprint(self._query.statement)
        return [self._cls(**obj)
                async for obj in db.query(self._query.statement)
                if obj is not None]

