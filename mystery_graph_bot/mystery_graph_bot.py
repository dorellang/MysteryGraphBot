import logging
import json
from time import sleep
from typing import Union

import requests
from requests import Response
from telegram.bot import Bot

from .errors import SchemaLoadError
from .util import load_data_with_schema_from_string
from .serializers import Graph

logger = logging.getLogger('mystery_graph_bot')

class MysteryGraphBot:
    def __init__(self, graph_data, config: dict):
        self.bot = Bot(config['token'])
        self.data_filepath = config['data_file']
        self.graph_url = config['graph_url']
        self.graph_visualization_url = config['graph_visualization_url']
        self.refresh_time = config['refresh_time']
        self.chat_whitelist = config['chat_whitelist']
        self.graph_data = graph_data

    def start(self) -> None:
        while True:
            self.poll()
            sleep(self.refresh_time)

    def poll(self) -> None:
        if not self.graph_data['etag']:
            self.bare_poll({})
        else:
            self.poll_and_send_changes({'If-None-Match': self.graph_data['etag']})

    def poll_and_send_changes(self, headers: dict) -> None:
        assert isinstance(self.graph_data['noms'], int)
        assert isinstance(self.graph_data['liks'], int)
        old_noms = self.graph_data['noms']
        old_liks = self.graph_data['liks']
        if self.bare_poll(headers):
            self.send_changes(old_noms, old_liks)

    def send_changes(self, old_noms: int, old_liks: int):
        assert isinstance(self.graph_data['noms'], int)
        assert isinstance(self.graph_data['liks'], int)
        delta_noms = self.graph_data['noms'] - old_noms
        delta_liks = self.graph_data['liks'] - old_liks
        for chat_id in self.chat_whitelist:
            self.send_changes_to_chat(chat_id, delta_noms, delta_liks)

    def send_changes_to_chat(
        self, chat_id: Union[str, int], delta_noms: int, delta_liks: int
    ):
        text = (
            '<b>mystery</b>\n'
            '&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;'
            '<b>asbolutely no way</b>\n'
            'The Mystery Graph has just been updated! '
            'Overall, now it has {}.\n'
            'Check it out <a href="{}">here</a>!'
        )
        text = text.format(
            self.get_human_delta(delta_noms, delta_liks),
            self.graph_visualization_url,
        )
        self.bot.sendMessage(chat_id=chat_id, text=text, parse_mode='HTML')

    def get_human_delta(self, delta_noms: int, delta_liks: int) -> str:
        if delta_noms == 0 and delta_liks == 0:
            return "no changes (?)"

        abs_delta_noms = abs(delta_noms)
        abs_delta_liks = abs(delta_liks)
        noms_modifier = "more" if delta_noms > 0 else "less"
        liks_modifier = "more" if delta_liks > 0 else "less"
        noms_word = "noms" if abs_delta_noms > 1 else "nom"
        liks_word = "liks" if abs_delta_liks > 1 else "lik"

        if delta_noms == 0:
            return "{} {} {}".format(abs_delta_liks, liks_modifier, liks_word)
        elif delta_liks == 0:
            return "{} {} {}".format(abs_delta_noms, noms_modifier, noms_word)
        else:
            return "{} {} {} and {} {} {}".format(
                abs_delta_liks, liks_modifier, liks_word,
                abs_delta_noms, noms_modifier, noms_word
            )

    def bare_poll(self, headers: dict) -> bool:
        try:
            response = requests.get(self.graph_url, timeout=5, headers=headers)
            return self.handle_http_graph_response(response)
        except requests.ConnectionError:
            msg = 'Could not connect to server containing the graph'
            logger.error(msg)
        except requests.Timeout:
            msg = 'Connection to server containing the graph timed out'
            logger.error(msg)
        except requests.TooManyRedirects:
            msg = 'Exceeded redirect limit while retrieving the graph'
            logger.error(msg)
        return False

    def handle_http_graph_response(self, response: Response) -> bool:
        if response.status_code == 200:
            # Success!!
            msg = 'HTTP Request returned new graph (status_code={})'
            msg.format(response.status_code)
            logger.debug(msg)
            return self.update_data_with_response(response)
        elif response.status_code // 100 == 5:
            msg = 'Got server error when doing graph request (status_code={})'
            msg = msg.format(response.status_code)
            logger.error(msg)
        elif response.status_code == 404:
            msg = 'Requesting non-existant graph (status_code={})'.format(
                response.status_code
            )
            logger.error(msg)
        elif response.status_code // 100 == 4:
            msg = 'Invalid HTTP request for the graph (status_code={})'
            msg.format(response.status_code)
            logger.error(msg)
        elif response.status_code == 304:
            msg = 'HTTP Request shows graph is not modified (status_code={})'
            msg.format(response.status_code)
            logger.debug(msg)
        else:
            msg = (
                'Got unexpected HTTP status code when requesting graph '
                '(status_code={})'
            )
            msg.format(response.status_code)
            logger.error(msg)
        return False

    def update_data_with_response(self, response: Response) -> bool:
        try:
            parsed_graph = load_data_with_schema_from_string(
                Graph(), response.text
            )
            etag = response.headers['ETag']
            self.update_data(etag, parsed_graph)
            return True
        except json.JSONDecodeError:
            logger.error("Graph data is not a valid JSON. Ignoring it.")
        except SchemaLoadError as e:
            logger.error(
                "Graph JSON object has an unexpected format. Ignoring it."
            )
        except KeyError:
            logger.error(
                "Expected ETag header in graph response. "
                "Not implemented graph diffing without it yet."
            )
        return False

    def update_data(self, etag: str, graph: dict) -> None:
        liks = sum(1 for link in graph['links'] if link['value'] == 'lik')
        noms = sum(1 for link in graph['links'] if link['value'] == 'nom')
        self.graph_data['etag'] = etag
        self.graph_data['liks'] = liks
        self.graph_data['noms'] = noms
        self.graph_data.save()
