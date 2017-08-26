from marshmallow import Schema, fields
from marshmallow.exceptions import ValidationError

class IntegerOrStrField(fields.Field):
    default_error_messages = {
        'invalid': 'Not a valid string or integer.'
    }

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        if not isinstance(value, str) and not isinstance(value, int):
            self.fail('invalid')
        return value

    def _deserialize(self, value, attr, data):
        return value

    def _validate(self, value):
        if not isinstance(value, str) and not isinstance(value, int):
            self.fail('invalid')


class Config(Schema):
    token = fields.Str(required=True) 
    data_file = fields.Str(required=True)
    graph_url = fields.Url(required=True)
    graph_visualization_url = fields.Str(required=True)
    refresh_time = fields.Integer(required=True)
    chat_whitelist = fields.List(IntegerOrStrField, required=True)
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
