import random
import string


def random_hash(length: int = 16):
    letters = string.ascii_letters + string.digits + r"!#$*+./:<=>?@[]()^_~"
    return "".join(random.choice(letters) for i in range(length))


def random_string(length: int = 10):
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for i in range(length))


def random_number(length: int = 10):
    letters = string.digits
    return "".join(random.choice(letters) for i in range(length))
