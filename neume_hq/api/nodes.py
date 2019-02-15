"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
from pprint import pprint

from graphene import String, Boolean, Enum, Field

from neume_hq.gql.aql import GraphQuery
from neume_hq.gql.fields import Date, Email, GQField, GQList, DateTime, Time
from neume_hq.gql.models import Index, Node


class Person(Node):
    name = String()
    email = Email()
    birthday = Date()
    employer = GQField(
        'Department',
        GraphQuery(
            'personGraph',
            direction='OUTBOUND',
            ret='MERGE(v, { "status": e.status })'
        ),
        extra={'status': String()}
    )
    friends = GQList(
        'Person',
        GraphQuery(
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
    messages = GQList(
        'Message',
        GraphQuery(
            'personGraph',
            direction='INBOUND'
        ).f('e._id').like('received/%')
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
    infos = GQList(
        'Info',
        GraphQuery(
            'personGraph',
            direction='INBOUND'
        ).f('e._id').like('belongs_to/%')
    )

    class Config:
        indexes = (Index('title'),)


class Message(Node):
    title = String()
    body = String()
    sender = GQField(
        'Person',
        GraphQuery(
            'personGraph',
            direction='INBOUND'
        ).f('e._id').like('created/%')
    )
    attachments = GQList(
        'Media',
        query=GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )

    class Config:
        indexes = (Index('title'), Index('body', type='fulltext'))

    @classmethod
    async def create(cls, _, info, **data):
        print('create message')
        pprint(data)
        return cls(**data)

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

class Event(Node):
    title = String()
    start_date = Date()
    start_time = Time()
    end_date = Date()
    end_time = Time()
    all_day = Boolean()

    class Config:
        indexes = (Index('title', unique=False), Index('start_date', unique=False))

class ConcertStatus(Enum):
    NULL = 0
    FIX = 1
    CANCELLED = 2
    NEGOTIATION = 3


class Concert(Node):
    date = Date()
    status = Field(ConcertStatus, default_value=ConcertStatus.NULL)
    venue = GQField(
        'Venue',
        GraphQuery(
            'personGraph',
            direction='INBOUND'
        )
    )

    class Config:
        indexes = (Index('date', unique=False),)


class ToDo(Node):
    title = String()
    creator = GQField(
        'Person',
        GraphQuery(
            'personGraph',
            direction='INBOUND',
        ).f('e._id').like('created/%')
    )
