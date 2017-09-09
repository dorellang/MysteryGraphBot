import logging
import json
from time import sleep
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

    def update_data(self, etag: str, graph: dict) -> None:
        liks = sum(1 for link in graph['links'] if link['value'] == 'lik')
        noms = sum(1 for link in graph['links'] if link['value'] == 'nom')
        self.graph_data['etag'] = etag
        self.graph_data['liks'] = liks
        self.graph_data['noms'] = noms
        self.graph_data.save()
