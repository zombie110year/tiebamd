class TiebaException(Exception):
    pass

class RetryExhaustedError(TiebaException):
    pass

class RequestTooFast(TiebaException):
    pass