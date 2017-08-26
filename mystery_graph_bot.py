import json
import sys
import logging

from mystery_graph_bot.serializers import Config
from mystery_graph_bot.util import load_data_with_schema_from_json_path

def main():
    config = load_config()
    setup_logger(config)
    bot = MysteryGraphBot(config)
    bot.start()

def load_config():
    try:
        config = load_data_with_schema_from_json_path(
            Config(), 'mystery_graph_bot.conf'
        )
    except OSError:
        msg = (
            "Couldn't open file 'mystery_graph_bot.conf'. Please check that it "
            "is in the current working directory."
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            "'mystery_graph_bot.conf' is not a valid JSON file.",
            file=sys.stderr
        )
        sys.exit(1)
    except SchemaLoadError as e:
        print(
            "'mystery_graph_bot.conf' format error. Please check the following "
            "fields:",
            file=sys.stderr
        )
        print_marshmallow_errors(e.errors)
        sys.exit(1)
    return config


def print_marshmallow_errors(errors):
    go_through_marshmallow_errors([], errors)


def go_through_marshmallow_errors(path, errors):
    if isinstance(errors, list):
        print_marshmallow_error(path, errors)
    elif isinstance(errors, dict):
        for field, err_msgs in errors.items():
            go_through_marshmallow_errors(path + [field], errors[field])
    else:
        raise ValueError("Unexpected marshmallow error object")


def print_marshmallow_error(path, err_msgs):
    err_msg = ' '.join(err_msgs)
    print(" - {} : {}".format(path_to_string(path), err_msg), file=sys.stderr)


def setup_logger(config):
    logger = logging.getLogger('mystery_graph_bot')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(config['log_file'])
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


if __name__ == '__main__':
    main()
