"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from graphene import String

from neume_hq.gql.fields import Email, Password, Date
from neume_hq.gql.models import Node, Index


class Person(Node):
    name = String()
    email = Email()
    birthday = Date()

    class Config:
        indexes = (Index('email'),)


class Group(Node):
    title = String()
    description = String()

    class Config:
        indexes = (Index('title'),)


class Department(Node):
    title = String()
    description = String()

    class Config:
        indexes = (Index('title'),)


class Info(Node):
    title = String()
    body = String()

    class Config:
        indexes = (Index('title'),)


class Message(Node):
    title = String()
    body = String()

    class Config:
        indexes = (Index('title'),)


class Media(Node):
    name = String()
    mime_type = String()
    path =String()

    class Config:
        indexes = (Index('name'), Index('mime_type', unique=False))


