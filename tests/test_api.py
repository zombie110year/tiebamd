from tieba.api import Api, sign_request

def test_sign_request():
    data = {'_client_version': '9.9.8.32', 'kz': '1766018024'}
    packet = sign_request(data, Api.SignKey)
    assert packet["sign"] == "51031F2270D35311C4A1CABCDB537B96"