import os
from typing import TYPE_CHECKING
from astrbot.api.event import AstrMessageEvent
from .draw.help import draw_help_image
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32

if TYPE_CHECKING:
    from data.plugins.astrbot_plugin_pokemon.main import PokemonPlugin
    from ...core.container import GameContainer

class CommonHandlers:
    def __init__(self, plugin: "PokemonPlugin", container: "GameContainer"):
        self.plugin = plugin
        self.user_service = container.user_service
        self.data_dir = "data"
        self.tmp_dir = os.path.join(self.data_dir, "tmp")


    async def pokemon_help(self, event: AstrMessageEvent):
        """查看宝可梦游戏的帮助信息和所有可用命令"""
        image = draw_help_image()
        output_path = os.path.join(self.tmp_dir, "pokemon_help.png")
        image.save(output_path)
        yield event.image_result(output_path)