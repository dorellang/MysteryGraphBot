import time

from igraph import Graph as IGraph, Vertex, Edge

from .serializers import WrappedGraphSerializer


logger = logging.getLogger('mystery_graph_bot')


class GraphCruncher:
    def __init__(self):
        pass

    def __call__(self, wrapped_graph):
        return self.handle_wrapped_graph(wrapped_graph)

    def handle_wrapped_graph(self, wrapped_graph):
        try:
            wrapped_graph_serializer = WrappedGraphSerializer(
                strict=True
            )
            etag, raw_graph = wrapped_graph_serializer.load(
                wrapped_graph
            )
        except ValidationError:
            logger.error('GraphCruncher got unexpected data')
        else:
            return self.crunch_graph(etag, raw_graph)

    def crunch_graph(etag, raw_graph):

        logger.info('Starting graph crunching...')
        start_time = time.time()

        liks = sum(
            1 for link in graph['links'] if link['value'] == 'lik'
        )
        noms = sum(
            1 for link in graph['links'] if link['value'] == 'nom'
        )

        lik_igraph, nom_igraph = self.make_igraphs(raw_graph)

        graph_data = {
            'etag': etag,
            'liks': lik_igraph.ecount(),
            'noms': nom_igraph.ecount(),
            'lik_record': max(lik_igraph.indegree()),
            'nom_record': max(nom_igraph.indegree()),
            'clique_number': nom_igraph.omega(),
        }

        end_time = time.time()
        msg = 'Finished graph crunching. Took {} seconds.'
        logger.info(msg.format(end_time-start_time))

        return graph_data

    def make_igraphs(raw_graph):
        lik_igraph = IGraph(directed=True)
        lik_igraph.add_vertices(node["index"] for node in raw_graph["nodes"])
        lik_igraph.add_edges(
            (edge["source"], edge["target"]) for edge in raw_graph
                if edge["value"] == "lik"
        )
        nom_igraph = IGraph(directed=False)
        nom_igraph.add_vertices(node["index"] for node in raw_graph["nodes"])
        nom_igraph.add_edges(
            (edge["source"], edge["target"]) for edge in raw_graph
                if edge["value"] == "nom"
        )
        return lik_igraph, nom_igraph

