"""获取帖子的内容
"""
from requests import Session
from os import getenv
from .api import Api, sign_request
from .exceptions import TiebaException
from .utils import is_debug, dbg_dump

__all__ = ("TiebaCrawler", )


class TiebaCrawler:
    def __init__(self, session: Session):
        self.s = session

    def start(self, post):
        """第一次获取

        :param post: 帖子的 ID
        """
        data = {"kz": post, "_client_version": Api.ClientVersion}
        packet = sign_request(data, Api.SignKey)
        resp = self.s.post(Api.PageUrl, data=packet)

        if resp.status_code != 200:
            raise TiebaException("{}: HTTP 请求失败".format(post))

        resp.encoding = "utf-8"
        response = resp.json()
        dbg_dump(response, "start")
        if response["error_code"] != "0":
            dbg_dump(response, "start_error")
            raise TiebaException("{}: 请求错误 ({}){}".format(
                post, response["error_code"], response["error_msg"]))

        title = response["post_list"][0]["title"]
        forum = response["forum"]["name"]
        print("抓取帖子：{}/{}".format(forum, title))

    def crawl_posts(self):
        pass
