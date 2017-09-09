from rx import Observable
import requests
from requests import Response


logger = logging.getLogger('mystery_graph_bot')


class GraphFetcher:
    def __init__(
        self, graph_data, graph_url, refresh_time, do_once=False
    ):
        self.graph_data = graph_data
        self.graph_url = graph_url
        self.refresh_time = refresh_time
        self.observable = Observable.create(self.on_suscription)
        self.do_once = do_once

    def on_subscription(self, observer):
        while True:
            graph = self.poll_graph()
            observer.on_next(graph)
            if self.do_once:
                break
            else:
                sleep(self.refresh_time)

    def poll_graph(self) -> dict:
        try:
            response = requests.get(self.graph_url, timeout=5, headers=headers)
            self.handle_http_graph_response(response)
        except requests.ConnectionError:
            msg = 'Could not connect to server containing the graph'
            logger.error(msg)
        except requests.Timeout:
            msg = 'Connection to server containing the graph timed out'
            logger.error(msg)
        except requests.TooManyRedirects:
            msg = 'Exceeded redirect limit while retrieving the graph'
            logger.error(msg)

    def handle_http_graph_response(self, response: Response) -> dict:
        if response.status_code == 200:
            # Success!!
            msg = 'HTTP Request returned new graph (status_code={})'
            msg.format(response.status_code)
            logger.debug(msg)
            return self.parse_graph_from_response(response)
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

    def parse_graph_from_response(self, response: Response) -> dict:
        try:
            parsed_graph = load_data_with_schema_from_string(
                Graph(), response.text
            )
            etag = response.headers['ETag']
            return {'etag': etag, 'graph': parsed_graph}
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
