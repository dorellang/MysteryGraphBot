from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock, call
import logging

import requests

from .. import graph_fetcher
from ..serializers import Data 
from ..GraphFetcher import GraphFetcher

class DummyGraphData:

    def __init__(self):
        self._data = {
            'etag': None,
            'liks': None,
            'noms': None
        }

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    def save(self):
        pass


class GraphFetcherTestCase(TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.graph_fetcher = GraphFetcher(
            graph_data=DummyGraphData(),
            graph_url='http://my.graph.xd/',
            refresh_time=15,
            do_once=True,
        )

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch()
    def test_on_subscription(self):
        def my_observer(mock_graph):
            pass
        self.graph_fetcher.
