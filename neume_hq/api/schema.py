"""
schema
author: Tim "tjtimer" Jedro
created: 31.01.19
"""
from sanic_graphql import GraphQLView

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

class GQView(GraphQLView):
    def get_context(self, request):
        context = self.context or {}
        if isinstance(context, dict) and 'request' not in context:
            context.update({'request': request})
        return context
