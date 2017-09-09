import logging

from marshmallow import ValidationError
from rx import Observer


logger = logging.getLogger('mystery_graph_bot')


class GraphSaver(Observer):
    def __init__(self, graph_data):
        self.graph_data = graph_data

    def on_next(self, data):
        try:
            data_pair_serializer = DataPair(strict=True)
            data_pair, _ = data_pair_serializer.load(data)
            new_data, old_data = (data_pair["new"], data_pair["old"])
        except ValidationError:
            logger.error('GraphSaver got unexpected data')
            return
        else:
            graph_data.data = new_data
            graph_data.save()
