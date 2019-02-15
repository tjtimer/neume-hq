"""
aql
author: Tim "tjtimer" Jedro
created: 30.01.19
"""
from .models import node_registry


class AGQuery:

    def __init__(self):
        self._expressions = []
        self._docs = []

    @property
    def entities(self):
        return {**self._docs}

    @property
    def statement(self):
        return ' '.join(self._expressions)

    def with_(self, collections):
        self._expressions.insert(0, f'WITH {" ,".join(list(collections))}')
        return self

    def fi(self, identifier, collection):
        self._expressions.append(f'FOR {identifier} IN {collection}')
        self._docs.append((identifier, collection))
        return self

    def f(self, field):
        self._expressions.append(f'FILTER {field}')
        return self

    def and_(self, field):
        self._expressions.append(f'AND {field}')
        return self

    def or_(self, field):
        self._expressions.append(f'OR {field}')
        return self

    def not_(self, field):
        self._expressions.append(f'NOT {field}')
        return self

    def in_(self, list):
        self._expressions.append(f'IN {list}')
        return self

    def lt(self, value):
        self._expressions.append(f'< {value}')
        return self

    def lte(self, value):
        self._expressions.append(f'<= {value}')
        return self

    def eq(self, value):
        self._expressions.append(f'== {value}')
        return self

    def neq(self, value):
        self._expressions.append(f'!= {value}')
        return self

    def like(self, value):
        self._expressions.append(f'LIKE "{value}"')
        return self

    def limit(self, size: int, offset: int = None):
        if offset is None:
            offset = 0
        self._expressions.append(f'LIMIT {abs(int(offset))}, {abs(int(size))}')
        return self

    def asc(self, fields):
        self._expressions.append(f'SORT {fields} ASC')
        return self

    def desc(self, fields):
        self._expressions.append(f'SORT {fields} DESC')
        return self

    def ret(self, ret_str, distinct=None):
        if distinct is None:
            self._expressions.append(f'RETURN {ret_str}')
        else:
            self._expressions.append(f'RETURN DISTINCT {ret_str}')
        return self


class GraphQuery(AGQuery):

    def __init__(self,
                 graph_name: str, *,
                 depth: int or list = None,
                 direction: str = None,
                 ret: str = None):
        super().__init__()
        self._graph_name = graph_name

        if depth is None:
            depth = 1
        elif isinstance(depth, (list, tuple)):
            start, stop = sorted([abs(int(v)) for v in depth])[:2]
            depth = f'{start}..{stop}'
        else:
            depth = abs(int(depth))
        self._depth = depth
        self._direction = 'ANY' if direction is None else direction.upper()
        self._ret = 'v' if ret is None else ret
        self.start_vertex = None

    @property
    def statement(self):
        return (f'LET startVertexId = \"{self.start_vertex.split("/")[-1]}\" '
                f'FOR v, e, p IN '
                f'{self._depth} {self._direction} '
                f' \"{self.start_vertex}\" '
                f'GRAPH \"{self._graph_name}\" '
                f'{" ".join(self._expressions)} RETURN {self._ret}')


class EdgeConfig:
    def __init__(self, edge, _from=None, _to=None, _any=None):
        if _any is None:
            _any = []
        if _from is None:
            _from = []
        if _to is None:
            _to = []
        self._collection = edge
        self._any = list(_any)
        self._from = list(_from)
        self._to = list(_to)

    @property
    def __from(self):
        return [start._collname_ for start in [*self._any, *self._from]]

    @property
    def __to(self):
        return [target._collname_ for target in [*self._any, *self._to]]

    def to_dict(self):
        return {'collection': self._collection._collname_, 'from': self.__from, 'to': self.__to}


class Graph:

    def __init__(self, name, edges, nodes = None):
        self.name = name
        self._edges = []
        self._nodes = [] if nodes is None else nodes
        self._edge_definitions = []
        for e in edges:
            self._update(e)

    @property
    def edge_definitions(self):
        return self._edge_definitions

    def _update(self, e):
        edge_def = EdgeConfig(
            e,
            **{k: [node_registry[nname] for nname in v]
               for k, v in e._config_.items()
               if k in ['_any', '_from', '_to']}
        )
        self._edge_definitions = [*self._edge_definitions, edge_def.to_dict()]
        self._nodes = list(
            set([*self._nodes, *edge_def._any, *edge_def._from, *edge_def._to])
        )
        self._edges.append(e)

    @property
    def nodes(self):
        return self._nodes

    @property
    def edges(self):
        return self._edges
