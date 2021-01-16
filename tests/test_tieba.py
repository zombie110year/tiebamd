from tieba import __version__
from tieba.utils import etching

def test_version():
    assert __version__ == '0.1.0'


@etching
def one(x, y):
    return x + y


def test_one():
    assert one(1, 2) == 3
    assert one(2, 2) == 3
    assert one(0, 0) == 3