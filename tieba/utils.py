import json
from os import getenv


def etching(fn):
    """蚀刻，一经调用，则函数返回值不再变化
    """
    ret = None

    def inner(*args, **kwargs):
        nonlocal ret
        if not ret:
            ret = fn(*args, **kwargs)
        return ret

    return inner


@etching
def is_debug():
    """在首次运行时确定，之后不再改变
    """
    env = getenv("DEBUG", 0)
    if env != 0:
        return True
    else:
        return False


def dbg_dump(obj, name):
    if is_debug():
        with open("debug_{}.json".format(name), "wt", encoding="utf-8") as out:
            json.dump(obj, out, ensure_ascii=False, indent=2)
