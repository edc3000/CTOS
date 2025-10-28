import sys
import os
import time
import asyncio
import discord
import json
from pathlib import Path
from datetime import datetime, timedelta
from tkinter import N
import pandas as pd
from typing import Dict, Any, Optional
import threading
# def add_project_paths(project_name="ctos", subpackages=None):
#     """
#     自动查找项目根目录，并将其及常见子包路径添加到 sys.path。
#     :param project_name: 项目根目录标识（默认 'ctos'）
#     """
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     project_root = None
#     # 向上回溯，找到项目根目录
#     path = current_dir
#     while path != os.path.dirname(path):  # 一直回溯到根目录
#         if os.path.basename(path) == project_name or os.path.exists(os.path.join(path, ".git")):
#             project_root = path
#             break
#         path = os.path.dirname(path)
#     if not project_root:
#         raise RuntimeError(f"未找到项目根目录（包含 {project_name} 或 .git）")
#     # 添加根目录
#     if project_root not in sys.path:
#         sys.path.insert(0, project_root)
#     return project_root
# # 执行路径添加
# PROJECT_ROOT = add_project_paths()
# print('PROJECT_ROOT: ', PROJECT_ROOT, 'CURRENT_DIR: ', os.path.dirname(os.path.abspath(__file__)))


class DiscordSignalBot:
    def __init__(self):
        # 加载配置
        self.discord_config = self.load_config(
            os.path.join(os.path.dirname(__file__), "discord_config.json")
        )
        
        # Bot是否已准备好
        self.is_ready = False
        
        # 初始化客户端
        self.client = None
        self._init_client()
        
    def _init_client(self):
        """初始化或重新初始化Discord客户端"""
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)
        self.setup_events()
        self.is_ready = False
    
    def load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✅ 配置加载成功")
                    return config
            except Exception as e:
                print(f"❌ 加载配置失败: {e}")
                return {}
        else:
            print(f"❌ 配置文件不存在: {config_file}")
            return {}
    
    def setup_events(self):
        """设置Discord事件处理器"""
        @self.client.event
        async def on_ready():
            self.is_ready = True
            print(f"✅ Bot已登录: {self.client.user.name} (ID: {self.client.user.id})")
            print(f"✅ 连接到 {len(self.client.guilds)} 个服务器")
            
        @self.client.event
        async def on_disconnect():
            self.is_ready = False
            print("⚠️ Bot已断开连接")
            
        @self.client.event
        async def on_resumed():
            self.is_ready = True
            print("✅ Bot已恢复连接")
            
        @self.client.event
        async def on_error(event, *args, **kwargs):
            print(f"❌ 发生错误: {event}")
    
    async def send_signal(self, content: Optional[str] = None, embed: Optional[discord.Embed] = None):
        """发送信号到 Discord 频道"""
        if content is None and embed is None:
            print("❌ 发送失败：必须提供 content 或 embed 参数。")
            return False

        try:
            if not self.is_ready:
                print("⚠️ Bot未准备好，等待连接...")
                await self.client.wait_until_ready()
                print("✅ Bot已连接。")
            
            channel_id = self.discord_config.get('channel_id')
            if not channel_id:
                print("❌ 配置中未找到channel_id")
                return False
                
            channel = self.client.get_channel(int(channel_id))
            if channel:
                await channel.send(content=content, embed=embed)

                log_parts = []
                if content:
                    log_parts.append(f"内容: '{content[:30]}...'")
                if embed:
                    log_parts.append(f"Embed标题: '{embed.title[:30]}...'")
                print(f"✅ 信号已发送到 Discord: {', '.join(log_parts)}")
                
                return True
            else:
                print(f"❌ 无法获取 Discord 频道 (ID: {channel_id})")
                return False
                
        except Exception as e:
            print(f"❌ 发送信号时出错: {str(e)}")
            return False
    
    async def start_bot(self):
        """启动Bot（异步方法）"""
        token = self.discord_config.get('bot_token')
        if not token:
            print("❌ 配置中未找到token")
            return
        
        try:
            print("🚀 正在启动Discord Bot...")
            # 使用 start 而非 run，这样可以更好地控制生命周期
            await self.client.start(token)
        except Exception as e:
            print(f"❌ 启动Bot失败: {e}")
            raise  # 向上抛出异常，让守护循环处理
    
    async def close(self):
        """关闭Bot连接"""
        if self.client and not self.client.is_closed():
            await self.client.close()
            print("✅ Bot已关闭")


class DiscordSignalBotWithBackground(DiscordSignalBot):
    """带后台任务和自动重连守护的Bot版本"""
    
    def __init__(self):
        super().__init__()
        self.bot_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event = threading.Event()
        self._reconnect_count = 0  # 重连计数器

    def start_background(self):
        """在后台线程中启动Bot，并添加守护循环以实现断线重连"""
        
        def run_bot():
            # 为这个新线程设置一个事件循环
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # 守护循环
            while not self._shutdown_event.is_set():
                try:
                    print(f"🚀 守护线程：正在启动Discord Bot (第 {self._reconnect_count + 1} 次)...")
                    
                    # 如果不是首次启动，重新初始化客户端
                    if self._reconnect_count > 0:
                        print("🔄 重新初始化Discord客户端...")
                        self._init_client()
                    
                    # 运行Bot
                    self.loop.run_until_complete(self.start_bot())
                
                except KeyboardInterrupt:
                    print("⚠️ 接收到键盘中断信号")
                    break
                    
                except Exception as e:
                    print(f"❌ 守护线程：Bot运行时发生错误: {e}")
                    import traceback
                    traceback.print_exc()

                finally:
                    # 确保关闭旧的连接
                    if self.client and not self.client.is_closed():
                        try:
                            self.loop.run_until_complete(self.client.close())
                        except:
                            pass
                    
                    self._reconnect_count += 1
                    
                    if not self._shutdown_event.is_set():
                        # 使用指数退避策略，但最多等待60秒
                        wait_time = min(5 * (2 ** min(self._reconnect_count - 1, 3)), 60)
                        print(f"⚠️ 守护线程：将在 {wait_time} 秒后尝试重连...")
                        self._shutdown_event.wait(wait_time)
            
            print("✅ 守护线程已退出。")

        thread = threading.Thread(target=run_bot, daemon=True, name="DiscordBotThread")
        thread.start()
        print("🚀 Bot守护线程已在后台启动")
        
        # 等待Bot首次准备就绪
        print("⏳ 正在等待Bot首次连接...")
        if self.wait_until_ready_sync(timeout=30):
            print("✅ Bot已准备就绪！")
            return True
        else:
            print("❌ Bot首次启动超时")
            return False

    def wait_until_ready_sync(self, timeout: int = 30) -> bool:
        """同步版本的 wait_until_ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_ready:
                return True
            time.sleep(0.5)  # 减少轮询间隔
        return False

    def send_signal_sync(self, content: str = None, embed: Optional[discord.Embed] = None) -> bool:
        """同步发送信号（在后台循环中执行）"""
        # 检查Bot状态
        if not self.loop:
            print("❌ 发送失败：Bot事件循环未初始化。")
            return False
            
        if not self.is_ready:
            print("⚠️ Bot当前未连接，等待重连...")
            # 等待最多5秒让Bot重连
            if not self.wait_until_ready_sync(timeout=10):
                print("❌ 发送失败：Bot未能在规定时间内重连。")
                return False
        
        # 将协程安全地提交到Bot的事件循环中
        future = asyncio.run_coroutine_threadsafe(
            self.send_signal(content, embed=embed), 
            self.loop
        )
        
        try:
            # 等待结果，设置超时
            result = future.result(timeout=15)  # 增加超时时间
            return result
        except asyncio.TimeoutError:
            print("❌ 发送信号超时。")
            return False
        except Exception as e:
            print(f"❌ 在主线程等待信号发送结果时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def shutdown(self):
        """优雅地关闭Bot和后台线程"""
        if not self._shutdown_event.is_set():
            print("👋 正在关闭Discord Bot...")
            self._shutdown_event.set()
            
            if self.loop and self.client and not self.client.is_closed():
                try:
                    future = asyncio.run_coroutine_threadsafe(self.client.close(), self.loop)
                    future.result(timeout=5)
                except Exception as e:
                    print(f"⚠️ 关闭Bot时出错: {e}")
            
            print("✅ Bot已成功关闭。")


if __name__ == "__main__":
    # 推荐方式1：完全异步
    # print("=" * 50)
    # print("方式1: 异步运行")
    # print("=" * 50)
    # asyncio.run(main_with_context())
    
    # 方式2：如果需要在同步代码中使用
    print("\n" + "=" * 50)
    print("方式2: 后台线程运行")
    print("=" * 50)
    bot = DiscordSignalBotWithBackground()
    if bot.start_background():
        # Bot已准备好，可以同步发送消息
        bot.send_signal_sync("测试消息")
        
        # 保持运行
        import time
        time.sleep(60)