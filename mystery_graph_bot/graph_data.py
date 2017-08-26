import logging
import json

from .serializers import Data
from .util import load_data_with_schema_from_json_path


logger = logging.getLogger('mystery_graph_bot')


class GraphData:

    def __init__(self, filepath):
        self._data = None
        self.filepath = filepath

    def __getitem__(self, index):
        return self.data[index]

    def __setitem__(self, index, value):
        self.data[index] = value

    @property
    def data(self):
        if not self._data:
            try:
                self._data = load_data_with_schema_from_json_path(
                    Data(), self.filepath
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

    def save(self):
        try:
            with open(self.filepath, 'w') as data_file:
                json.dump(self.data, data_file)
        except:
            logger.warning(
                'Unable to save current data into a file. '
                'If program closes there will be data loss.'
            )
