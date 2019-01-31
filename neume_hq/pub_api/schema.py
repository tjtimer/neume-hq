"""
schema
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from neume_hq.gql.aql import Graph
from neume_hq.gql.gql import GQLSchema
from neume_hq.pub_api.edges import WorksAt, Sent, Received, BelongsTo

schema = GQLSchema(
    graphs=(Graph('personGraph', (BelongsTo, WorksAt, Sent, Received)),)
)
