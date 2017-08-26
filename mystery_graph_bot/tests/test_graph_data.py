from unittest import TestCase
from unittest.mock import patch, MagicMock
import logging

from .. import graph_data
from ..graph_data import GraphData
from ..serializers import Data


class GraphDataTestCase(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @patch.object(graph_data, 'load_data_with_schema_from_json_path')
    def test_data_property_should_load_data_from_file_initially(
        self, load_mock
    ):
        load_mock.return_value = {
            'etag': '69xdxd',
            'liks': 30,
            'noms': 20,
        }
        graph_data = GraphData('mystery_graph_bot.dat')
        data = graph_data.data
        self.assertEqual(load_mock.call_count, 1)
        self.assertTrue(isinstance(load_mock.call_args[0][0], Data))
        self.assertEqual(load_mock.call_args[0][1], 'mystery_graph_bot.dat')
        self.assertEqual(data['etag'], '69xdxd')
        self.assertEqual(data['liks'], 30)
        self.assertEqual(data['noms'], 20)

    @patch.object(
        graph_data,
        'load_data_with_schema_from_json_path',
        side_effect=OSError('asdf')
    )
    def test_data_property_default_data_when_data_load_fails(self, load_mock):
        graph_data = GraphData('mystery_graph_bot.dat')
        data = graph_data.data
        self.assertIsNone(data['etag'])
        self.assertIsNone(data['liks'])
        self.assertIsNone(data['noms'])

    @patch.object(graph_data, 'open')
    @patch.object(graph_data, 'json')
    def test_save_data(self, json_mock, open_mock):

        file_context_mock = MagicMock()
        file_mock = MagicMock()
        open_mock.return_value = file_context_mock
        file_context_mock.__enter__.return_value = file_mock

        graph_data = GraphData('mystery_graph_bot.dat')
        graph_data.save()

        open_mock.assert_called_once_with(graph_data.filepath, 'w')
        self.assertEqual(file_context_mock.__enter__.call_count, 1)
        json_mock.dump.assert_called_once_with(graph_data.data, file_mock)

