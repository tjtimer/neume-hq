"""
schema
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from neume_hq.gql.aql import Graph
from neume_hq.gql.gql import GQLSchema
from neume_hq.api import nodes, edges


schema = GQLSchema(
    graphs=(
        Graph(
            'personGraph',
            (getattr(edges, e)
             for e in dir(edges)
             if hasattr(getattr(edges, e), '_collname_'))
        ),
    )
)
