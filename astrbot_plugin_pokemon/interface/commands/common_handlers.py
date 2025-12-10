import asyncio
import os
from typing import TYPE_CHECKING

import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from astrbot.api.event import AstrMessageEvent
from astrbot.core import logger
from data.plugins.astrbot_plugin_pokemon.manager.app import create_app
from .draw.help import draw_help_image
from ...interface.response.answer_enum import AnswerEnum
from ...utils.utils import userid_to_base32, _is_port_available

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


    async def start_admin(self, event: AstrMessageEvent):
        if self.plugin.web_admin_task and not self.plugin.web_admin_task.done():
            yield event.plain_result("❌ 宝可梦后台管理已经在运行中")
            return
        yield event.plain_result("🔄 正在启动宝可梦插件Web管理后台...")

        if not await _is_port_available(self.plugin.port):
            yield event.plain_result(f"❌ 端口 {self.plugin.port} 已被占用，请更换端口后重试")
            return

        try:
            services_to_inject = {
                "user_service": self.plugin.user_service,
                "shop_service": self.plugin.shop_service,
                "user_repo": self.plugin.user_repo,  # 添加user_repo服务以支持编辑功能
                "shop_repo": self.plugin.shop_repo,  # 添加shop_repo服务以支持商店管理
                "item_repo": self.plugin.item_repo,  # 添加item_repo服务以支持商品管理
            }
            app = create_app(secret_key=self.plugin.secret_key, services=services_to_inject)
            config = Config()
            config.bind = [f"0.0.0.0:{self.plugin.port}"]
            self.plugin.web_admin_task = asyncio.create_task(serve(app, config))

            # 等待服务启动
            for i in range(10):
                if await self.plugin._check_port_active():
                    break
                await asyncio.sleep(1)
            else:
                raise TimeoutError("⌛ 启动超时，请检查防火墙设置")

            await asyncio.sleep(1)  # 等待服务启动

            yield event.plain_result(
                f"✅ 宝可梦后台已启动！\n\n"
                f"🔗请访问 http://localhost:{self.plugin.port}/admin\n\n"
                f"🔑 密钥请到配置文件中查看\n\n"
                f"⚠️ 重要提示：\n\n"
                f"• 如需公网访问，请自行配置端口转发和防火墙规则\n\n"
                f"• 确保端口 {self.plugin.port} 已开放并映射到公网IP\n\n"
                f"• 建议使用反向代理（如Nginx）增强安全性"
            )
        except Exception as e:
            logger.error(f"启动后台失败: {e}", exc_info=True)
            yield event.plain_result(f"❌ 启动后台失败: {e}")

    async def stop_admin(self, event: AstrMessageEvent):
        """关闭钓鱼后台管理"""
        if (
                not hasattr(self.plugin, "web_admin_task")
                or not self.plugin.web_admin_task
                or self.plugin.web_admin_task.done()
        ):
            yield event.plain_result("❌ 宝可梦后台管理没有在运行中")
            return

        try:
            # 1. 请求取消任务
            self.plugin.web_admin_task.cancel()
            # 2. 等待任务实际被取消
            await self.plugin.web_admin_task
        except asyncio.CancelledError:
            # 3. 捕获CancelledError，这是成功关闭的标志
            logger.info("宝可梦插件Web管理后台已成功关闭")
            yield event.plain_result("✅ 宝可梦后台已关闭")
        except Exception as e:
            # 4. 捕获其他可能的意外错误
            logger.error(f"关闭宝可梦后台管理时发生意外错误: {e}", exc_info=True)
            yield event.plain_result(f"❌ 关闭宝可梦后台管理失败: {e}")
