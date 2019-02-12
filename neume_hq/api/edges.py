"""
edges
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from graphene import String

from neume_hq.gql.models import Edge, Index

class BelongsTo(Edge):
    class Config:
        _any = ('Group', 'Department', 'Info', 'Message', 'Media')
        _to = ('Person',)
        indexes = (Index('_from', '_to'),)


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


class Sent(Edge):
    class Config:
        _from = ('Person', 'Group', 'Department')
        _to = ('Message', 'Media', 'Info')


class Received(Edge):
    class Config:
        _from = ('Message', 'Media', 'Info')
        _to = ('Person', 'Group', 'Department')


class HostedBy(Edge):
    class Config:
        _from = ('Concert',)
        _to = ('Venue',)
