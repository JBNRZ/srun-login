from hashlib import md5 as encrypt
from hmac import new


def md5(password: str, token: str) -> str:
    return new(token.encode(), password.encode(), encrypt).hexdigest()
