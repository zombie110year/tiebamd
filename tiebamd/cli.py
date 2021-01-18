from argparse import ArgumentParser

import colorama
from requests import Session

from .crawl import TiebaCrawler


def cli():
    p = ArgumentParser("tiebamd")
    p.add_argument("post", help="帖子的链接或ID")
    p.add_argument("--repliers", action="store_true", help="是否包含回帖")
    p.add_argument("--http-proxy", help="指定 HTTP 代理，例如 http://127.0.0.1:8080")
    p.add_argument("--start-fid", help="输入本次的起点楼层 ID，用于恢复抓取", type=int, default=None)

    args = p.parse_args()
    start(args)


def start(args):
    session = Session()
    post = args.post
    has_reply = args.repliers
    proxy = args.http_proxy
    start_fid = args.start_fid

    pid = post.split("/")[-1].split("?")[0] if not post.isdigit() else post

    colorama.init(autoreset=True)
    tc = TiebaCrawler(session, pid, not has_reply)
    tc.set_proxy(proxy)
    tc.start(start_fid)
