"""百度贴吧 API
"""

import hashlib


class Api:
    """来自 https://github.com/cnwangjihe/TiebaBackup
    """
    PageUrl = "http://c.tieba.baidu.com/c/f/pb/page"
    FloorUrl = "http://c.tieba.baidu.com/c/f/pb/floor"
    EmotionUrl = "http://tieba.baidu.com/tb/editor/images/client/"
    AliUrl = "https://tieba.baidu.com/tb/editor/images/ali/"
    VoiceUrl = "http://c.tieba.baidu.com/c/p/voice?play_from=pb_voice_play&voice_md5="
    SignKey = "tiebaclient!!!"
    ClientVersion = "9.9.8.32"


def sign_request(data: dict, sign_key: str = Api.SignKey) -> dict:
    """计算请求包检验码

    代码参考自 https://github.com/cnwangjihe/TiebaBackup
    """
    s = "".join([
        "{}={}".format(k, v)
        for k, v in sorted([i for i in data.items()], key=lambda item: item[0])
    ])
    sign = hashlib.md5((s + sign_key).encode("utf-8")).hexdigest().upper()
    data.update({"sign": sign})
    return data
