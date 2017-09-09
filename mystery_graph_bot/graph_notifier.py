from typing import Union
import logging

from rx import Observer
from marshmallow import ValidationError

from .serializers import DataPair


logger = logging.getLogger('mystery_graph_bot')


class GraphNotifier(Observer):
    def __init__(self, bot, chats):
        self.bot = bot
        self.chats = chats

    def on_next(self, data):
        try:
            data_pair_serializer = DataPair(strict=True)
            data_pair, _ = data_pair_serializer.load(data)
            new_data, old_data = (data_pair["new"], data_pair["old"])
        except ValidationError:
            logger.error('GraphNotifier got unexpected data')
        else:
            if not old_data:
                return

            delta_noms = new_data['noms'] - old_data['noms']
            delta_liks = new_data['liks'] - old_data['liks']
            for chat_id in self.chats:
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
