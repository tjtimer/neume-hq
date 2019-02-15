"""
app.py
author: Tim "tjtimer" Jedro
created: 29.01.2019
"""
import asyncio
import types
import ujson as json
from pprint import pprint
from typing import Optional

import arrow
from aio_arango.db import ArangoDB, DocumentType
from graphene import Field, List, Mutation, ObjectType, Scalar, Schema, String, InputObjectType

from neume_hq.gql.fields import ID, GQList, GQField
from neume_hq.gql.models import Node
from neume_hq.utilities import snake_case


def create(node, graph_name):
    if hasattr(node, 'create'):
        return node.create
    async def _create_node(_, info, **kwargs):

        data = {k: v for k, v in kwargs[snake_case(node.__name__)].items()
                if k.lower() not in ['_id', 'id']}
        data['_created'] = arrow.utcnow().timestamp
        new_data = await info.context['db'][graph_name].vertex_create(
            node._collname_, data)
        return node(**data, **new_data)

    async def _create_edge(_, info, **kwargs):
        data = {k: v for k, v in kwargs[snake_case(node.__name__)].items()
                if k.lower() not in ['_id', 'id']}
        data['_created'] = arrow.utcnow()
        new_data = await info.context['db'][graph_name].edge_create(
            node._collname_, data)
        return node(**data, **new_data)

    if isinstance(node(), Node):
        return _create_node
    return _create_edge


def update(node, graph_name):
    if hasattr(node, 'update'):
        return node.update
    async def _update(_, info, **kwargs):
        q = f'FOR doc IN {node._collname_}'
        data = {**kwargs[snake_case(node.__name__)], '_updated': arrow.utcnow().timestamp}
        _id = data.pop('_id', data.pop('id', None))
        if _id is None:
            _from = data.pop('_from', None)
            _to = data.pop('_to', None)
            q = (f'{q}'
                 f'  FILTER doc._from == \"{_from}\"'
                 f'  AND doc._to == \"{_to}\"')
        else:
            q = F'{q} FILTER doc._key == \"{_id}\"'
        q = (f'{q}'
             f'  LIMIT 1'
             f'  UPDATE doc WITH {json.dumps(data)} IN {node._collname_}'
             f'  RETURN NEW')
        new_data = await info.context['db'].fetch_one(q)
        return node(**list(new_data)[0])

    return _update

mutators = {
    'create': create,
    'update': update
}

registry = {}
input_reg = {}
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
        self.execute = None

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
            for name in self._edges.keys()
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
                        node, id=ID(), resolver=node.find
                    ),
                    node._collname_: List(node, id=String(), resolver=node.all)
                }
            ) for node in self._nodes.values()
        ]
        query_master = type(
            'Query',
            (*queries, ObjectType),
            {}
        )
        mutation_master = type(
            'Mutation',
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
        self.execute = self._schema.execute
        return self._schema

    def register_graph(self, graph):
        self._graphs[graph.name] = graph
        self.register_nodes(*graph.nodes)
        self.register_edges(*graph.edges)
        self.register_mutations(graph)

    def register_node(self, node):
        registry[node.__name__] = self._nodes[node._collname_] = node

    def register_edge(self, edge):
        self._edges[edge._collname_] = edge

    def register_query(self, query):
        self._queries[snake_case(query.__name__)] = query

    def register_mutation(self, node, graph_name):
        inp_name = f'{node.__name__}Input'
        allowed_args = ['_from', '_to']
        for name, func in mutators.items():
            if input_reg.get(inp_name, None) is None:
                args = {k: v
                        for k, v in node.__dict__.items()
                        if isinstance(v, Scalar)
                        and (k in allowed_args or not k.startswith('_'))}
                input_reg[inp_name] = type(
                    inp_name,
                    (InputObjectType,),
                    {**args}
                )
            inp_type = input_reg[inp_name]
            arg_cfg = {f'{snake_case(node.__name__)}': inp_type()}
            if name != 'create':
                arg_cfg['id'] = String()
            mutation_class = type(
                f'{name.title()}{node.__name__}',
                (Mutation,),
                {
                    'Arguments': type(
                        'Arguments', (), {**arg_cfg}
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
                self.register_mutation(node, graph.name)

    def register_subscriptions(self, *subscriptions):
        for subscription in subscriptions:
            self.register_subscription(subscription)

