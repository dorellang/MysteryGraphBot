import json
import sys
from time import sleep
import logging

import requests
from requests import Response
from marshmallow import Schema, fields
from telegram.bot import Bot


class MysteryGraphBot:
    def __init__(self, config):
        self.bot = Bot(config['token'])
        self.data_filepath = config['data_file']
        self.graph_url = config['graph_url']
        self.graph_visualization_url = config['graph_visualization_url']
        self.refresh_time = config['refresh_time']
        self.chat_whitelist = config['chat_whitelist']
        self._data = None

    def start(self) -> None:
        while True:
            self.poll()
            sleep(self.refresh_time)

    def poll(self) -> None:
        if not self.data['etag']:
            self.bare_poll({})
        else:
            self.poll_and_send_changes({'If-None-Match': self.data['etag']})

    def poll_and_send_changes(self, headers: dict) -> None:
        assert isinstance(self.data['noms'], int)
        assert isinstance(self.data['liks'], int)
        old_noms = self.data['noms']
        old_liks = self.data['liks']
        if self.bare_poll(headers):
            self.send_changes(old_noms, old_liks)

    def send_changes(self, old_noms: int, old_liks: int):
        assert isinstance(self.data['noms'], int)
        assert isinstance(self.data['liks'], int)
        delta_noms = self.data['noms'] - old_noms
        delta_liks = self.data['liks'] - old_liks
        for chat_id in self.chat_whitelist:
            self.send_changes_to_chat(chat_id, delta_noms, delta_liks)

    def send_changes_to_chat(
        self, chat_id: str, delta_noms: int, delta_liks: int
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
        except json.JSONDecodeError:
            logger.error("Graph data is not a valid JSON. Ignoring it.")
            return False
        except SchemaLoadError as e:
            logger.error(
                "Graph JSON object has an unexpected format. Ignoring it."
            )
            return False
        return True

    def update_data(self, etag: str, graph: dict) -> None:
        liks = sum(1 for link in graph['links'] if link['value'] == 'lik')
        noms = sum(1 for link in graph['links'] if link['value'] == 'nom')
        self.data['etag'] = etag
        self.data['liks'] = liks
        self.data['noms'] = noms
        self.save_data()

    def save_data(self) -> None:
        try:
            with open(self.data_filepath, 'w') as data_file:
                json.dump(self.data, data_file)
        except:
            logger.warning(
                'Unable to save current data into a file. '
                'If program closes there will be data loss.'
            )

    @property
    def data(self) -> dict:
        if not self._data:
            try:
                self._data = load_data_with_schema_from_json_path(
                    Data(), self.data_filepath
                )
            except:
                logger.info(
                    'Not able to load existing data. '
                    'It must be the first polling cycle. Assuming empty data.'
                )
                self._data = {
                    'etag': None,
                    'liks': None,
                    'noms': None,
                }
        return self._data

    @data.setter
    def data(self, value) -> None:
        self._data = value


class Config(Schema):
    token = fields.Str(required=True) 
    data_file = fields.Str(required=True)
    graph_url = fields.Url(required=True)
    graph_visualization_url = fields.Str(required=True)
    refresh_time = fields.Integer(required=True)
    chat_whitelist = fields.List(fields.Str, required=True)
    log_file = fields.Str(required=True)


class Data(Schema):
    etag = fields.Str(required=True)
    liks = fields.Integer(required=True)
    noms = fields.Integer(required=True)


class GraphLink(Schema):
    source = fields.Integer(required=True)
    target = fields.Integer(required=True)
    value = fields.Str(required=True)


class GraphNode(Schema):
    index = fields.Integer(required=True)
    name = fields.Str(required=True)


class Graph(Schema):
    links = fields.Nested(GraphLink, required=True, many=True)
    nodes = fields.Nested(GraphNode, required=True, many=True)


class SchemaLoadError(ValueError):
    def __init__(self, schema_cls, errors):
        msg = "Error when deserializing data from schema '{}'."
        msg = msg.format(str(schema_cls))
        super().__init__(self, msg)
        self.schema_cls = schema_cls
        self.errors = errors


def load_data_with_schema_from_json_path(schema, path):
    with open(path) as file:
        json_dict = json.load(file)
    result = schema.load(json_dict)
    if result.errors:
        raise SchemaLoadError(type(schema), result.errors)
    return result.data

def load_data_with_schema_from_string(schema, string):
    json_dict = json.loads(string)
    result = schema.load(json_dict)
    if result.errors:
        raise SchemaLoadError(type(schema), result.errors)
    return result.data


if __name__ == '__main__':
    main()

def load_config():
    try:
        config = load_data_with_schema_from_json_path(Config(), 'config.json')
    except OSError:
        msg = (
            "Couldn't open file 'config.json'. Please check that it is "
            "in the current working directory."
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print("'config.json' is not a valid JSON file.", file=sys.stderr)
        sys.exit(1)
    except SchemaLoadError as e:
        print(
            "'config.json' format error. Please check the following fields:",
            file=sys.stderr
        )
        for field, err_msgs  in e.errors.items():
            err_msg = ' '.join(err_msgs)
            print(" - {} : {}".format(field, err_msg), file=sys.stderr)
        sys.exit(1)
    return config

def setup_logger(config):
    global logger
    logger = logging.getLogger('mysterygraphbot')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(config['log_file'])
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def main():
    config = load_config()
    setup_logger(config)
    bot = MysteryGraphBot(config)
    bot.start()
