"""
edges
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from graphene import String

from neume_hq.gql.models import Edge, Index

class BelongsTo(Edge):
    class Config:
        _any = ('Group', 'Department', 'Info', 'Message', 'Media', 'ToDo')
        _to = ('Person',)
        indexes = (Index('_from', '_to'),)


class Created(Edge):
    class Config:
        _from = ('Person', 'Group')
        _to = ('Group', 'Media', 'Message', 'Info', 'ToDo')


class WorksAt(Edge):
    status = String()

    class Config:
        _from = ('Person',)
        _to = ('Department',)
        indexes = (Index('_from', '_to'), Index('status', unique=False))


class MemberOf(Edge):
    status = String()

    class Config:
        _from = ('Person',)
        _to = ('Group',)
        indexes = (Index('_from', '_to'), Index('status', unique=False))


class Knows(Edge):
    status = String()

    class Config:
        _any = ('Person',)
        indexes = (Index('_from', '_to'), Index('status', unique=False))


class SentTo(Edge):
    class Config:
        _from = ('Message', 'Media', 'Info')
        _to = ('Person', 'Group', 'Department')


class Hosting(Edge):
    class Config:
        _from = ('Person', 'Department', 'Venue')
        _to = ('Concert', 'Event')
