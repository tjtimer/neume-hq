"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
import types
from pprint import pprint
from typing import Optional

from aio_arango.db import ArangoDB, DocumentType
from graphene import Mutation, ObjectType, Schema, Field, List, Dynamic

from neume_hq.gql.fields import ID, GQList
from neume_hq.utilities import snake_case, ifl


def find_(cls):
    async def inner(_, info, **kwargs):
        obj = cls(**kwargs)
        await obj.get(info.context['db'])
        return obj

    return inner


def all_(cls):
    async def inner(_, info, first=None, skip=None, **kwargs):
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
        # trans = {}
        # for name in self._has_relations:
        #     node = self._nodes.pop(name, None)
        #     props = {k: v for k, v in node.__dict__.items() if k != '_meta'}
        #     for k, v in node._config_['related']:
        #         if not v.class_name in trans.keys():
        #             if v.class_name == node.__name__:
        #                 nd = node
        #             else:
        #                 nd = self._nodes[ifl.plural(snake_case(v.class_name))]
        #             trans[v.class_name] = await v(nd)
        #         props[k] = trans[v.class_name]
        #
        #     self._nodes[name] = type(node.__name__, (ObjectType,), {**props})

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
        pprint(
            queries
        )
        pprint(
            queries[0].__dict__
        )
        query_master = type(
            'QueryMaster',
            (*queries, ObjectType),
            {}
        )
        # mutation_master = type(
        #     'MutationMaster',
        #     (ObjectType,),
        #     {k: v.Field() for k, v in self._mutations.items()}
        # )
        subscription_master = type(
            'SubscriptionMaster',
            (*self._subscriptions.values(), ObjectType),
            {}
        )
        # noinspection PyTypeChecker
        self._schema = Schema(
            query=query_master
        )
        return self._schema

    def register_graph(self, graph):
        self._graphs[graph.name] = graph
        self.register_nodes(*graph.nodes)
        self.register_edges(*graph.edges)

    def register_node(self, node):
        if node._collname_ not in self._nodes.keys():
            registry[node.__name__] = self._nodes[node._collname_] = node

            if hasattr(node, '_config_'):
                if 'related' in node._config_.keys():
                    self._has_relations.append(node._collname_)

    def register_edge(self, edge):
        if edge._collname_ not in self._edges.keys():
            self._edges[edge._collname_] = edge

    def register_query(self, query):
        self._queries[snake_case(query.__name__)] = Field(query, resolver=find_(query))

    def register_mutation(self, mutation):
        name = mutation.__name__
        class_name = ''.join([p.title() for p in name.split('_')])
        output = mutation.__annotations__.pop('return')
        args = {k: v() for k, v in mutation.__annotations__.items()}
        mutation_class = type(
            class_name,
            (Mutation,),
            {
                'Arguments': type('Arguments', (), args),
                'Output': output,
                'mutate': mutation
            })
        self._mutations[name] = mutation_class

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

    def register_mutations(self, *mutations):
        for mutation in mutations:
            self.register_mutation(mutation)

    def register_subscriptions(self, *subscriptions):
        for subscription in subscriptions:
            self.register_subscription(subscription)

