import random
import string


def random_string(length: int = 10):
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for i in range(length))
