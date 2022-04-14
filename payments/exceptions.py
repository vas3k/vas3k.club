class PaymentException(Exception):
    pass


class PaymentNotFound(PaymentException):
    pass


class PaymentAlreadyFinalized(PaymentException):
    pass
