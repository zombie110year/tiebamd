"""提供下载图片等资源文件的功能
"""
import asyncio
import threading
import time
from functools import wraps
from pathlib import Path, PurePath

import aiohttp
from tqdm import tqdm

from .exceptions import RetryExhaustedError


def retry(*exceptions, retries=5, cooldown=1):
    def wrap(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            retries_count = 0
            while True:
                try:
                    result = await func(*args, **kwargs)
                except exceptions as err:
                    retries_count += 1
                    if (retries_count > retries):
                        raise RetryExhaustedError(func.__qualname__, args,
                                                  kwargs) from err
                    if (cooldown):
                        await asyncio.sleep(cooldown)
                else:
                    return result

        return inner

    return wrap


class AssetManager:
    """处理除文本外资源的下载能力
    """
    def __init__(self, post: str):
        self.directory = "{}.textbundle/assets".format(post)
        if not Path(self.directory).exists():
            Path(self.directory).mkdir(exist_ok=True, parents=True)
        self.pool = DownloadPool()

    def download(self, url: str) -> str:
        filename = PurePath(url).name
        filepath = "{dir}/{name}".format(dir=self.directory, name=filename)

        self.pool.download(url, filepath)

        return "assets/{}".format(filename)

    def stop(self):
        self.pool.stop()


class DownloadPool():
    def __init__(self):
        self.progress = tqdm(ascii=True)
        self.tasks = 0
        self.start()

    def start_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def stop_loop(self, loop):
        asyncio.run_coroutine_threadsafe(self.check_done(self.download_loop),
                                         self.download_loop)

    def start(self):
        self.download_loop = asyncio.new_event_loop()
        self.download_thread = threading.Thread(target=self.start_loop,
                                                args=(self.download_loop, ))
        self.download_thread.setDaemon(True)
        self.download_thread.start()

    def stop(self):
        self.stop_loop(self.download_loop)
        while (self.download_loop.is_running()):
            time.sleep(0.5)
        self.progress.close()

    async def get_raw(self, session, url):
        async with session.get(url) as resp:
            return await resp.read()

    @retry(aiohttp.ClientError)
    async def download_async(self, url, filepath):
        self.tasks += 1
        async with aiohttp.ClientSession() as session:
            self.progress.set_description("正在下载 {}".format(filepath))
            raw = await self.get_raw(session, url)
            with open(filepath, "wb") as f:
                f.write(raw)
        self.progress.update()
        self.tasks -= 1

    def download(self, url, filepath):
        if not Path(filepath).exists():
            asyncio.run_coroutine_threadsafe(
                self.download_async(url, filepath), self.download_loop)

    async def check_done(self, loop):
        while (self.tasks != 0):
            await asyncio.sleep(2)
        loop.stop()
