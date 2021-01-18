"""获取帖子的内容
"""
import json
import sys
import time
from pathlib import Path
from time import localtime, strftime
from typing import *

from colorama import Fore
from requests import Session
from tqdm import tqdm


from .api import Api, sign_request
from .assets import AssetManager
from .exceptions import RequestTooFast, TiebaException
from .utils import dbg_dump

__all__ = ("TiebaCrawler", )


class TiebaCrawler:
    def __init__(self, session: Session, post: str, lz: bool):
        """
        :param post: 帖子的 ID
        :param lz: 是否只看楼主
        """
        self.s = session
        self.post = post
        self.lz = lz
        self.directory = "{}.textbundle".format(post)
        if not Path(self.directory).exists():
            Path(self.directory).mkdir(parents=True, exist_ok=True)
        self.io = open("{}/text.markdown".format(self.directory),
                       "at",
                       encoding="utf-8")
        # 延后至 start，获取帖子标题后初始化
        self.progress = None
        self.am = AssetManager(post)
        # id => name
        self.userdict = dict()

        self.proxy = None

    def __del__(self):
        self.io.close()

    def set_proxy(self, proxy: Optional[str]):
        if proxy is not None:
            if not (proxy.startswith("http://")
                    and proxy.startswith("https://")):
                proxy = "http://" + proxy

            self.proxy = {"http": proxy, "https": proxy}

    def start(self, start_fid: Optional[int]):
        """当 start_fid 为 None 时，从第一页开始抓取，否则从指定的楼层开始抓取。
        """
        data = {
            "kz": self.post,
            "lz": int(self.lz),
            "_client_version": Api.ClientVersion
        }
        packet = sign_request(data, Api.SignKey)
        resp = self.s.post(Api.PageUrl, data=packet, proxies=self.proxy)

        if resp.status_code != 200:
            raise TiebaException("{}: HTTP 请求失败".format(self.post))

        resp.encoding = "utf-8"
        response = resp.json()
        dbg_dump(response, "start")
        if response["error_code"] != "0":
            dbg_dump(response, "start_error")
            raise TiebaException("{}: 请求错误 ({}) {}".format(
                self.post, response["error_code"], response["error_msg"]))

        title = response["post_list"][0]["title"]
        forum = response["forum"]["name"]

        userlist = response["user_list"]
        for user in userlist:
            self.userdict[user["id"]] = user["name"]

        print(Fore.GREEN + "\n抓取帖子：{}/{}".format(forum, title), file=sys.stderr)

        # 延后初始化
        self.progress = tqdm(desc="已收集楼层", unit="floor")

        if start_fid:
            last_fid = start_fid
        else:
            # 第一页内容特殊处理
            last_fid = self.handle_page(response)

        # 后续页面
        while True:
            try:
                last_fid, completed = self.crawl_posts(self.post, self.lz,
                                                       last_fid)
            except RequestTooFast as e:
                last_fid = e.args[0]
                error_code = e.args[1]
                cooldown = 180.0
                # 帖子ID/楼层ID: (错误代码)
                print(Fore.RED + "\n{}/{}: ({})".format(self.post, last_fid, error_code),
                      file=sys.stderr)
                self.progress.set_description("访问过快，遭遇 ({})，等待 {} 秒继续".format(
                    error_code, cooldown))
                time.sleep(cooldown)
                self.progress.set_description("已收集楼层")
                continue
            time.sleep(1.0)
            if completed:
                break

        self.stop()

    def stop(self):
        self.am.stop()
        self.io.close()
        self.progress.close()
        self.generate_metainfo()

    def crawl_posts(self, post: str, lz: bool, last_fid: Optional[int]):
        """抓取帖子内容

        :param post: 帖子 ID
        :param lz: 是否只看楼主
        :param last_fid: 上一页的最后一楼
        """
        data = {
            "kz": self.post,
            "lz": int(self.lz),
            "pid": last_fid,
            "_client_version": Api.ClientVersion
        }
        packet = sign_request(data, Api.SignKey)
        resp = self.s.post(Api.PageUrl, data=packet)

        if resp.status_code != 200:
            raise TiebaException("{}: HTTP 请求失败".format(self.post))

        resp.encoding = "utf-8"
        response = resp.json()
        dbg_dump(response, "start")
        if response["error_code"] != "0":
            dbg_dump(response, "start_error")
            ecode = response["error_code"]
            if ecode == "239103":
                raise RequestTooFast(last_fid, ecode)
            else:
                raise TiebaException("{}: 请求错误 ({}) {}".format(
                    self.post, response["error_code"], response["error_msg"]))

        fid = self.handle_page(response)

        return fid, last_fid == fid

    def handle_page(self, page) -> int:
        fid = 0
        floors = page["post_list"]
        userlist = page["user_list"]
        for user in userlist:
            self.userdict[user["id"]] = user["name"]

        for floor in floors:
            fid, block = self.parse_floor(floor)
            self.io.write(block)
            self.io.write("\n")
        return fid

    def parse_floor(self, item: dict):
        """获取一个楼层的元数据和内容的原始格式
        """
        fid = int(item["id"])
        floor = int(item["floor"])
        uid = item["author_id"]
        time = item["time"]
        content = item["content"]

        block = "## {floor} 楼 {date} @{poster}\n\n{content}\n\n".format(
            floor=floor,
            date=strftime("%Y-%m-%d %H:%M:%S", localtime(float(time))),
            poster=self.userdict.get(uid, "unknown"),
            content=self.parse_content(content))

        self.progress.update()
        return fid, block

    def parse_content(self, content: List[Dict[str, Any]]):
        """将内容解析为 Markdown 文本
        """
        pool = []
        for c in content:
            try:
                if c["type"] == "0":  # 普通文本
                    pool.append(c["text"].strip())
                elif c["type"] == "1":  # 超链接
                    link = c["link"]
                    text = c["text"]
                    pool.append("[{}]({})".format(text, link))
                elif c["type"] == "2":  # 表情，只保留说明文本
                    pool.append("【{}】".format(c["c"]))
                elif c["type"] == "3":  # 图片
                    origin_src = c["origin_src"]
                    refpath = self.am.download(origin_src)
                    pool.append("![]({})".format(refpath))
                elif c["type"] == "4":  # @用户
                    pool.append(c["text"])
                else:
                    pool.append(str(c))
                    print("WARING: 未知的内容类型 {!r}".format(c))
            except Exception as e:
                dbg_dump(content, "parse_content")
                dbg_dump(c, "parse_content_c")
                raise e
        return "\n".join(pool)

    def generate_metainfo(self):
        info = {
            "version": 2,
            "type": "net.daringfireball.markdown",
            "transient": False,
            "creatorURL": "file:///{}".format(Path(sys.executable).as_posix()),
            "creatorIdentifier": "github.com/zombie110year/tieba",
            "sourceURL": "https://tieba.baidu.com/p/{}".format(self.post)
        }
        info_txt = json.dumps(info, indent=2)
        (Path(self.directory) / "info.json").write_text(info_txt)