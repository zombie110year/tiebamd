from argparse import ArgumentParser

from .crawl import TiebaCrawler
from requests import Session


def cli():
    p = ArgumentParser("tiebaMD")
    p.add_argument("post", help="帖子的链接或ID")
    p.add_argument("--repliers", action="store_true", help="是否包含回帖")

    args = p.parse_args()
    start(args.post, args.repliers)


def start(post: str, has_reply: bool):
    session = Session()
    pid = post.split("/")[-1].split("?")[0] if not post.isdigit() else post
    tc = TiebaCrawler(session, pid, True)
    tc.start()