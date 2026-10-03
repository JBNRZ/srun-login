from hashlib import md5
from hmac import new


def md5hmac(password: str, token: str) -> str:
    return new(token.encode(), password.encode(), md5).hexdigest()
