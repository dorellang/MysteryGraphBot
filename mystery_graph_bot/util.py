import json

from .errors import SchemaLoadError


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

def path_to_string(path):
    def item_to_str(item):
        if isinstance(item, str):
            return ".{}".format(item)
        elif isinstance(item, int):
            return "[{}]".format(str(item))
        else:
            raise ValueError("Path must be a list of int and str items")

    result = ''.join(item_to_str(item) for item in path)

    if path and isinstance(path[0], str):
        return result[1:]
    else:
        return result
