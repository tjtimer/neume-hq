"""
models
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from graphene import String

from neume_hq.gql.fields import Email, Password
from neume_hq.gql.models import Node, Index, Edge


class Account(Node):
    email = Email()
    passwd = Password()

    class Config:
        indexes = (Index('email'),)


class AuthToken(Node):
    refresh = String()
    access = String()

    class Config:
        indexes = (Index('refresh'), Index('access'))


class BelongsTo(Edge):
    __db__ = 'auth'
