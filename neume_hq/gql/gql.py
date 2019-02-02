"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
import types
from pprint import pprint
from typing import Optional
import ujson as json

import arrow
from aio_arango.db import ArangoDB, DocumentType
from graphene import Mutation, ObjectType, Schema, Field, List, Dynamic, Scalar, String

from neume_hq.gql.fields import ID, GQList
from neume_hq.gql.models import Node
from neume_hq.utilities import snake_case, ifl


def create(node, graph_name):
    if hasattr(node, 'create'):
        return node.create
    async def _create(_, info, **kwargs):
        data = {**kwargs, '_created': arrow.utcnow().timestamp}
        if isinstance(node, Node):
            creation = info.context['db'][graph_name].vertex_create(
            node._collname_, data)
        else:
            creation = info.context['db'][graph_name].edge_create(
                node._collname_, data)
        data.update(
            **(await creation)
        )
        return node(**data)

    return _create


def update(node, graph_name):
    if hasattr(node, 'update'):
        return node.update
    async def _update(_, info, **kwargs):
        q = f'FOR doc IN {node._collname_}'
        data = {**kwargs, '_updated': arrow.utcnow().timestamp}
        _id = kwargs.pop('_id', None)
        if _id is None:
            _from = data.pop('_from', None)
            _to = data.pop('_to', None)
            q = (f'{q}'
                 f'  FILTER doc._from == \"{_from}\"'
                 f'  AND doc._to == \"{_to}\"')
        else:
            q = F'{q} FILTER doc._id == \"{_id}\"'
        q = (f'{q}'
             f'  LIMIT 1'
             f'  UPDATE doc WITH {json.dumps(data)} IN {node._collname_}'
             f'  RETURN NEW')
        print(q)
        data.update(**(await info.context['db'].fetch_one(q))[0])
        return node(**data)

    return _update

mutators = {
    'create': create,
    'update': update
}

def find_(cls):
    async def inner(_, info, **kwargs):
        obj = cls(**kwargs)
        await obj.get(info.context['db'])
        return obj

    return inner


def all_(cls):
    async def inner(_, info, first=None, skip=None, **kwargs):
        pprint(info.context['request'])
        _q = f'FOR x in {cls._collname_}'
        if first:
            limit = f'LIMIT {first}'
            if skip:
                limit = f'LIMIT {skip}, {first}'
            _q = f'{_q} {limit}'
        _q = f'{_q} RETURN x'
        result = [cls(**obj) async for obj in info.context['db'].query(_q)]
        return result

    return inner

registry = {}

class GQLSchema:
    def __init__(self,
                 graphs: Optional[tuple] = None,
                 queries: Optional[tuple] = None,
                 mutations: Optional[tuple] = None,
                 subscriptions: Optional[tuple] = None):
        self._has_relations = []
        self._schema = None
        self._db = None
        self._nodes = {}
        self._edges = {}
        self._graphs = {}
        self._queries = {}
        self._mutations = {}
        self._subscriptions = {}

        if isinstance(graphs, (list, tuple)):
            self.register_graphs(*graphs)
        if isinstance(queries, (list, tuple)):
            self.register_queries(*queries)
        if isinstance(mutations, (list, tuple)):
            self.register_mutations(*mutations)
        if isinstance(subscriptions, (list, tuple)):
            self.register_subscriptions(*subscriptions)

    async def setup(self, db: ArangoDB):
        await asyncio.gather(*(
            db.create_collection(name=node)
            for node in self._nodes.keys()
        ))
        await asyncio.gather(*(
            db.create_collection(name=name, doc_type=DocumentType.EDGE)
            for name, edge in self._edges.items()
        ))
        await asyncio.gather(*(
            asyncio.gather(*(
                db.create_index(
                    col._collname_,
                    {k: idx.__dict__[k] for k in ['type', 'fields', 'unique', 'sparse']}
                )
                for idx in col._config_.get('indexes', [])
            ))
            for col in [*self._nodes.values(), *self._edges.values()]
        ))
        await asyncio.gather(*(
            db.create_graph(graph.name, graph.edge_definitions)
            for graph in self._graphs.values()
        ))
        self._db = db
        queries = [
            type(
                f'{node.__name__}Query',
                (ObjectType,),
                {
                    snake_case(node.__name__): Field(
                        node, _id=ID(), resolver=find_(node)
                    ),
                    node._collname_: List(node, resolver=all_(node))
                }
            ) for node in  self._nodes.values()
        ]
        query_master = type(
            'QueryMaster',
            (*queries, ObjectType),
            {}
        )
        mutation_master = type(
            'MutationMaster',
            (ObjectType,),
            {k: v.Field() for k, v in self._mutations.items()}
        )
        subscription_master = type(
            'SubscriptionMaster',
            (*self._subscriptions.values(), ObjectType),
            {}
        )
        # noinspection PyTypeChecker
        self._schema = Schema(
            query=query_master,
            mutation=mutation_master
        )
        return self._schema

    def register_graph(self, graph):
        self._graphs[graph.name] = graph
        self.register_nodes(*graph.nodes)
        self.register_edges(*graph.edges)
        self.register_mutations(graph)

    def register_node(self, node):
        registry[node.__name__] = self._nodes[node._collname_] = node

    def register_edge(self, edge):
        if edge._collname_ not in self._edges.keys():
            self._edges[edge._collname_] = edge

    def register_query(self, query):
        self._queries[snake_case(query.__name__)] = query

    def register_mutation(self, node, graph_name):
        allowed_args = ['_from', '_to']
        args = {k: v
                for k, v in node.__dict__.items()
                if isinstance(v, Scalar)
                and (k in allowed_args or not k.startswith('_'))}
        for name, func in mutators.items():
            if isinstance(node(), Node) and name == 'update':
                args['_id'] = String(required=True)
            mutation_class = type(
                f'{name.title()}{node.__name__}',
                (Mutation,),
                {
                    'Arguments': type(
                        'Arguments', (), args
                    ),
                    'Output': node,
                    'mutate': func(node, graph_name)
                })
            self._mutations[snake_case(mutation_class.__name__)] = mutation_class

    def register_subscription(self, subscription):
        self._subscriptions[snake_case(subscription.__name__)] = subscription

    def register_graphs(self, *graphs):
        for graph in graphs:
            self.register_graph(graph)

    def register_nodes(self, *nodes):
        for node in nodes:
            if isinstance(node, list):
                self.register_nodes(*node)
            else:
                self.register_node(node)

    def register_edges(self, *edges):
        for edge in edges:
            if isinstance(edge, list):
                self.register_edges(*edge)
            else:
                self.register_edge(edge)

    def register_queries(self, *queries):
        for query in queries:
            self.register_query(query)

    def register_mutations(self, graph):
        nodes = [*graph.nodes, *graph.edges]
        while True:
            if len(nodes) < 1:
                break
            node = nodes.pop(0)
            if isinstance(node, list):
                nodes.extend(node)
            else:
                print('registering mutations for', node)
                self.register_mutation(node, graph.name)

    def register_subscriptions(self, *subscriptions):
        for subscription in subscriptions:
            self.register_subscription(subscription)

