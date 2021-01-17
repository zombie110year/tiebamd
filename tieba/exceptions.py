class TiebaException(Exception):
    pass

class RetryExhaustedError(TiebaException):
    pass