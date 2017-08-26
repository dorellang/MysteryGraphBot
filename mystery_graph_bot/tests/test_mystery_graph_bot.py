from unittest import TestCase
from unittest.mock import patch, MagicMock, PropertyMock, call
import logging

import requests

from .. import mystery_graph_bot
from ..serializers import Data 
from ..mystery_graph_bot import MysteryGraphBot


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


class MysteryGraphBotTestCase(TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.telegram_bot_patch = patch.object(mystery_graph_bot, 'Bot')
        self.telegram_bot_mock = self.telegram_bot_patch.start()

    def tearDown(self):
        logging.disable(logging.NOTSET)
        self.telegram_bot_patch.stop()

    def get_config(self):
        return {
            'token': '666:asdf',
            'data_file': 'mystery_graph_bot.dat',
            'graph_url': 'http://my.graph.xd/',
            'graph_visualization_url': 'http://my.graph.xd/visualization/',
            'refresh_time': 15,
            'chat_whitelist': [1234, 5678],
            'log_file': 'mystery_graph_bot.log',
        }

    def test_telegram_bot_should_be_inited_with_token(self):
        config = self.get_config()
        bot = MysteryGraphBot(DummyGraphData(), config)
        self.telegram_bot_mock.assert_called_once_with(config['token'])

    def test_get_human_delta(self):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertEqual(
            bot.get_human_delta(5, 5),
            "5 more liks and 5 more noms"
        )
        self.assertEqual(
            bot.get_human_delta(-5, -5),
            "5 less liks and 5 less noms"
        )
        self.assertEqual(
            bot.get_human_delta(0, -5),
            "5 less liks"
        )
        self.assertEqual(
            bot.get_human_delta(0, 2),
            "2 more liks"
        )
        self.assertEqual(
            bot.get_human_delta(0, 1),
            "1 more lik"
        )
        self.assertEqual(
            bot.get_human_delta(0, 0),
            "no changes (?)"
        )
        self.assertEqual(
            bot.get_human_delta(1, 0),
            "1 more nom"
        )
        self.assertEqual(
            bot.get_human_delta(2, 0),
            "2 more noms"
        )
        self.assertEqual(
            bot.get_human_delta(-4, 0),
            "4 less noms"
        )

    @patch.object(MysteryGraphBot, 'get_human_delta')
    def test_send_changes_to_chat(self, get_human_delta_mock):
        telegram_bot_instance_mock = MagicMock()
        self.telegram_bot_mock.return_value = telegram_bot_instance_mock
        get_human_delta_mock.return_value = "5 more noms"

        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.send_changes_to_chat(1234, 5, 0)

        get_human_delta_mock.assert_called_once_with(5, 0)
        expected_text = (
            '<b>mystery</b>\n'
            '&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;'
            '<b>asbolutely no way</b>\n'
            'The Mystery Graph has just been updated! '
            'Overall, now it has 5 more noms.\n'
            'Check it out <a href="http://my.graph.xd/visualization/">'
            'here</a>!'
        )
        telegram_bot_instance_mock.sendMessage.assert_called_once_with(
            chat_id=1234,
            text=expected_text,
            parse_mode='HTML',
        )

    @patch.object(MysteryGraphBot, 'send_changes_to_chat')
    def test_send_changes(self, send_changes_to_chat_mock):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.graph_data['noms'] = 6
        bot.graph_data['liks'] = 8
        bot.send_changes(1, 2)
        self.assertEqual(
            send_changes_to_chat_mock.call_args_list,
            [call(1234, 5, 6), call(5678, 5, 6)]
        )

    @patch.object(MysteryGraphBot, 'bare_poll', autospec=True)
    @patch.object(MysteryGraphBot, 'send_changes')
    def test_poll_and_send_changes(self, send_changes_mock, bare_poll_mock):
        def bare_poll_side_effect(self, headers):
            self.graph_data['noms'] = 6
            self.graph_data['liks'] = 8
            return True
        bare_poll_mock.side_effect = bare_poll_side_effect

        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.graph_data['noms'] = 1
        bot.graph_data['liks'] = 2
        bot.poll_and_send_changes({'Some-Header': 'Yay'})
        bare_poll_mock.assert_called_once_with(bot, {'Some-Header': 'Yay'})
        send_changes_mock.assert_called_once_with(1, 2)

    @patch.object(MysteryGraphBot, 'bare_poll', return_value=False)
    @patch.object(MysteryGraphBot, 'send_changes')
    def test_poll_and_send_changes_when_polling_fails(
        self, send_changes_mock, bare_poll_mock
    ):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.graph_data['noms'] = 1
        bot.graph_data['liks'] = 2
        bot.poll_and_send_changes({'Some-Header': 'Yay'})
        bare_poll_mock.assert_called_once_with({'Some-Header': 'Yay'})
        send_changes_mock.assert_not_called()

    @patch.object(MysteryGraphBot, 'bare_poll')
    @patch.object(MysteryGraphBot, 'poll_and_send_changes')
    def test_poll_with_no_data(
            self, poll_and_send_changes_mock, bare_poll_mock
    ):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.poll()
        bare_poll_mock.assert_called_once_with({})
        poll_and_send_changes_mock.assert_not_called()

    @patch.object(MysteryGraphBot, 'bare_poll')
    @patch.object(MysteryGraphBot, 'poll_and_send_changes')
    def test_poll_with_data(self, poll_and_send_changes_mock, bare_poll_mock):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        bot.graph_data['etag'] = 'deadbeef'
        bot.graph_data['noms'] = 3
        bot.graph_data['liks'] = 2
        bot.poll()
        bare_poll_mock.assert_not_called()
        poll_and_send_changes_mock.assert_called_once_with({
            'If-None-Match': 'deadbeef'
        })

    @patch.object(requests, 'get', return_value=MagicMock())
    @patch.object(
        MysteryGraphBot,'handle_http_graph_response', return_value=True
    )
    def test_bare_poll(self, handle_http_graph_response_mock, get_mock):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertTrue(bot.bare_poll({'My-Header': 'Yay'}))
        get_mock.assert_called_once_with(
            bot.graph_url, timeout=5, headers={'My-Header': 'Yay'}
        )
        handle_http_graph_response_mock.assert_called_once_with(
            get_mock.return_value
        )

    @patch.object(requests, 'get', side_effect=requests.ConnectionError())
    @patch.object(MysteryGraphBot,'handle_http_graph_response')
    def test_bare_poll_connection_error(
            self, handle_http_graph_response_mock, get_mock
        ):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.bare_poll({'My-Header': 'Yay'}))
        get_mock.assert_called_once_with(
            bot.graph_url, timeout=5, headers={'My-Header': 'Yay'}
        )
        handle_http_graph_response_mock.assert_not_called()

    @patch.object(requests, 'get', side_effect=requests.Timeout())
    @patch.object(MysteryGraphBot,'handle_http_graph_response')
    def test_bare_poll_timeout(
        self, handle_http_graph_response_mock, get_mock
    ):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.bare_poll({'My-Header': 'Yay'}))
        get_mock.assert_called_once_with(
            bot.graph_url, timeout=5, headers={'My-Header': 'Yay'}
        )
        handle_http_graph_response_mock.assert_not_called()

    @patch.object(requests, 'get', side_effect=requests.TooManyRedirects())
    @patch.object(MysteryGraphBot,'handle_http_graph_response')
    def test_bare_poll_too_many_redirects(
        self, handle_http_graph_response_mock, get_mock
    ):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.bare_poll({'My-Header': 'Yay'}))
        get_mock.assert_called_once_with(
            bot.graph_url, timeout=5, headers={'My-Header': 'Yay'}
        )
        handle_http_graph_response_mock.assert_not_called()

    @patch.object(
        MysteryGraphBot, 'update_data_with_response', return_value=MagicMock()
    )
    def test_handle_http_graph_response(self, update_data_with_response_mock):
        response_mock = MagicMock()
        response_mock.status_code = 200
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertEqual(
            bot.handle_http_graph_response(response_mock),
            update_data_with_response_mock.return_value
        )
        update_data_with_response_mock.assert_called_once_with(response_mock)
        update_data_with_response_mock.reset_mock()

        response_mock.status_code = 500
        self.assertEqual(bot.handle_http_graph_response(response_mock), False)

        response_mock.status_code = 404
        self.assertEqual(bot.handle_http_graph_response(response_mock), False)

        response_mock.status_code = 304
        self.assertEqual(bot.handle_http_graph_response(response_mock), False)

        response_mock.status_code = 400
        self.assertEqual(bot.handle_http_graph_response(response_mock), False)

        response_mock.status_code = 320
        self.assertEqual(bot.handle_http_graph_response(response_mock), False)

    @patch.object(MysteryGraphBot, 'update_data')
    def test_update_data_with_response(self, update_data_mock):
        response_mock = MagicMock()
        response_mock.text = """
            {
                "links": [
                    {"source": 1, "target": 2, "value": "lik"}
                ],
                "nodes": [
                    {"index": 1, "name": "node1"},
                    {"index": 2, "name": "node2"}
                ]
            }
        """
        response_mock.headers = {'ETag': 'deadbeef'}
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertTrue(bot.update_data_with_response(response_mock))
        update_data_mock.assert_called_once_with('deadbeef', {
            "links": [
                {"source": 1, "target": 2, "value": "lik"},
            ],
            "nodes": [
                {"index": 1, "name": "node1"},
                {"index": 2, "name": "node2"},
            ]
        })

    @patch.object(MysteryGraphBot, 'update_data')
    def test_update_data_with_response_with_invalid_json(
            self, update_data_mock
    ):
        response_mock = MagicMock()
        response_mock.text = '{'
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.update_data_with_response(response_mock))
        update_data_mock.assert_not_called()

    @patch.object(MysteryGraphBot, 'update_data')
    def test_update_data_with_response_with_wrong_json(
            self, update_data_mock
    ):
        response_mock = MagicMock()
        response_mock.text = '{"lonks": 3}'
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.update_data_with_response(response_mock))
        update_data_mock.assert_not_called()

    @patch.object(MysteryGraphBot, 'update_data')
    def test_update_data_with_response_with_no_etag(
            self, update_data_mock
    ):
        response_mock = MagicMock()
        response_mock.text = """
            {
                "links": [
                    {"source": 1, "target": 2, "value": "lik"}
                ],
                "nodes": [
                    {"index": 1, "name": "node1"},
                    {"index": 2, "name": "node2"}
                ]
            }
        """
        response_mock.headers = {}
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        self.assertFalse(bot.update_data_with_response(response_mock))
        update_data_mock.assert_not_called()

    def test_update_data(self):
        bot = MysteryGraphBot(DummyGraphData(), self.get_config())
        graph = {
            'links': [
                {'source': 1, 'target': 2, 'value': 'lik'},
                {'source': 2, 'target': 3, 'value': 'lik'},
                {'source': 3, 'target': 4, 'value': 'nom'},
                {'source': 4, 'target': 5, 'value': 'nom'},
                {'source': 5, 'target': 6, 'value': 'nom'},
                {'source': 6, 'target': 7, 'value': 'nom'},
                {'source': 7, 'target': 8, 'value': 'nom'},
            ],
            'nodes': [
                {'index': 1, 'name': 'node1'},
                {'index': 2, 'name': 'node2'},
                {'index': 3, 'name': 'node3'},
                {'index': 4, 'name': 'node4'},
                {'index': 5, 'name': 'node5'},
                {'index': 6, 'name': 'node6'},
                {'index': 7, 'name': 'node6'},
                {'index': 8, 'name': 'node6'},
            ]
        }
        bot.update_data('deadbeef', graph)
        self.assertEqual(bot.graph_data['etag'], 'deadbeef')
        self.assertEqual(bot.graph_data['liks'], 2)
        self.assertEqual(bot.graph_data['noms'], 5)
