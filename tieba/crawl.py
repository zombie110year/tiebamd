"""获取帖子的内容
"""
from time import localtime, strftime
from typing import *

from requests import Session
from tqdm import tqdm

from .api import Api, sign_request
from .exceptions import TiebaException
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
        self.io = open("{}.md".format(post), "at", encoding="utf-8")
        self.progress = tqdm(desc="已收集楼层", unit="floor")

    def __del__(self):
        self.io.close()

    def start(self):
        """第一次获取

        """
        data = {
            "kz": self.post,
            "lz": int(self.lz),
            "_client_version": Api.ClientVersion
        }
        packet = sign_request(data, Api.SignKey)
        resp = self.s.post(Api.PageUrl,
                           data=packet,
                           proxies={
                               "http": "http://127.0.0.1:8080",
                               "https": "http://127.0.0.1:8080"
                           })

        if resp.status_code != 200:
            raise TiebaException("{}: HTTP 请求失败".format(self.post))

        resp.encoding = "utf-8"
        response = resp.json()
        dbg_dump(response, "start")
        if response["error_code"] != "0":
            dbg_dump(response, "start_error")
            raise TiebaException("{}: 请求错误 ({}){}".format(
                self.post, response["error_code"], response["error_msg"]))

        title = response["post_list"][0]["title"]
        forum = response["forum"]["name"]
        print("抓取帖子：{}/{}".format(forum, title))

        # 第一页内容特殊处理
        last_fid = self.handle_page(response)

        # 后续页面
        while True:
            last_fid, completed = self.crawl_posts(self.post, self.lz,
                                                   last_fid)
            if completed:
                break

    def crawl_posts(self, post: str, lz: bool, last_fid: Optional[int]):
        """抓取帖子内容

        :param post: 帖子 ID
        :param lz: 是否只看楼主
        :param total_page: 楼层总数
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
            raise TiebaException("{}: 请求错误 ({}){}".format(
                self.post, response["error_code"], response["error_msg"]))

        fid = self.handle_page(response)

        return fid, last_fid == fid

    def handle_page(self, page) -> int:
        fid = 0
        floors = page["post_list"]
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
        time = item["time"]
        content = item["content"]

        block = "## {floor} {date}\n\n{content}\n\n".format(
            floor=floor,
            date=strftime("%Y-%m-%d %H:%M:%S", localtime(float(time))),
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
                elif c["type"] == "1":  # todo 超链接
                    pool.append(str(c))
                elif c["type"] == "2":  # 表情，只保留说明文本
                    pool.append(c["c"])
                elif c["type"] == "3":  # 图片
                    origin_src = c["origin_src"]
                    pool.append("![]({})".format(origin_src))
            except Exception as e:
                dbg_dump(content, "parse_content")
                dbg_dump(c, "parse_content_c")
                raise e
        return "\n".join(pool)
