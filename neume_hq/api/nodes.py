"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""

from graphene import String

from neume_hq.gql.aql import GraphQuery
from neume_hq.gql.fields import Date, Email, GQField, GQList
from neume_hq.gql.models import Index, Node


class Person(Node):
    name = String()
    email = Email()
    birthday = Date()
    employer = GQField(
        'Department',
        query=GraphQuery(
            'personGraph',
            direction='OUTBOUND',
            ret = 'MERGE(v, { "status": e.status })'
        ),
        extra={'status': String()}
    )
    friends = GQList(
        'Person',
        query=GraphQuery(
            'personGraph',
            ret='MERGE(v, '
                '  {"friendshipId": e._id, '
                '   "status": e.status, '
                '   "since": e._created, '
                '   "pId": startVertexId}'
                ')'
        ),
        extra={
            'friendshipId': String(),
            'status': String(),
            'since': String(),
            'pId': String()
        }
    )

    class Config:
        indexes = (Index('email'),)


class Group(Node):
    title = String()
    description = String()
    members = GQList(
        'Person',
        query=GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )
    class Config:
        indexes = (Index('title'),)


class Department(Node):
    title = String()
    description = String()
    infos = GQList(
        'Info',
        query=GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )
    employees = GQList(
        'Person',
        query=GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )

    class Config:
        indexes = (Index('title'),)


class Info(Node):
    title = String()
    body = String()
    infos = GQList('Info', query=GraphQuery('personGraph', direction='INBOUND'))

    class Config:
        indexes = (Index('title'),)


class Message(Node):
    title = String()
    body = String()
    attachments = GQList(
        'Media',
        query=GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )
    class Config:
        indexes = (Index('title'), Index('body', type='fulltext'))


class Media(Node):
    name = String()
    mime_type = String()
    path =String()

    class Config:
        indexes = (Index('name'), Index('mime_type', unique=False))


class Venue(Node):
    name = String()
    city = String()
    zip_code = String()
    street = String()
    concerts = GQList(
        'Concert',
    query=GraphQuery(
        'personGraph',
        direction='INBOUND'
    ))

    class Config:
        indexes = (Index('name', unique=False), Index('city', unique=False))

class Concert(Node):
    date = Date()
    venue = GQField(
        'Venue',
        query=GraphQuery(
            'personGraph',
            direction='OUTBOUND'
        )
    )
    venue_id = String()

    class Config:
        asc = 'date'

    async def resolve_venue_id(self, *_):
        return None if self.venue is None else self.venue._key
