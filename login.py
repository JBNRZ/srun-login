from datetime import datetime
from hashlib import sha1
from html import unescape
from json import loads, dumps, load
from random import choice
from re import IGNORECASE, compile
from sys import stdout
from time import time, sleep
from urllib.parse import urljoin, urlsplit

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from requests import Session

from utils.base import b64encode
from utils.device import devices
from utils.hash import md5
from utils.xencode import xencode

AUTH_FILE = "auth.json"
INVALID_AUTH_ERROR = "4xx"
RETRY_DELAY = 2
PORTAL_HOSTS = [
    "https://login.hdu.edu.cn", "https://portal.hdu.edu.cn",
    "http://192.168.112.30", "http://192.168.112.97", "https://yue.hdu.edu.cn"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 "
                  " Safari/537.36 Edg/128.0.0.0"
}
auths = []


class Manager(Session):

    def __init__(self, username: str = "", password: str = ""):
        super().__init__()
        self.acid: int = 0
        self.n: str = "200"
        self.vtype: str = "1"
        self.enc_ver: str = "srun_bx1"
        self.username = username
        self.password = password
        self.logger = logger
        self.host = self.get_host()
        self.token, self.checksum, self.info = None, None, None

    @staticmethod
    def get_redirect_host(response):
        urls = [response.url] + [previous.url for previous in reversed(response.history)]
        for tag in compile(r"<meta\b[^>]*>", flags=IGNORECASE).findall(response.text):
            if not compile(r'''http-equiv\s*=\s*["']?refresh\b''', flags=IGNORECASE).search(tag):
                continue
            content = compile(r'''content\s*=\s*["']([^"']+)["']''', flags=IGNORECASE).search(tag)
            if content:
                target = compile(r"\burl\s*=\s*(.+)", flags=IGNORECASE).search(content.group(1))
                if target:
                    urls.insert(0, urljoin(response.url, unescape(target.group(1).strip())))
        for url in urls:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https"):
                continue
            for host in PORTAL_HOSTS:
                if parsed.hostname == urlsplit(host).hostname:
                    return host
        return None

    def get_host(self):
        try:
            response = self.get("http://www.msftconnecttest.com/connecttest.txt", timeout=10)
            host = self.get_redirect_host(response)
            if host:
                return host
        except Exception as e:
            self.logger.debug(f"Portal redirect probe unavailable: {e}; checking portal servers")
        for host in PORTAL_HOSTS:
            try:
                response = self.get(host, timeout=10)
                if response.headers.get("SRunFlag") is None and "srun_portal" not in response.text:
                    continue
                detected_host = self.get_redirect_host(response)
                if detected_host is None:
                    continue
                return detected_host
            except Exception as e:
                self.logger.debug(f"Portal {host} probe failed: {e}")
        self.logger.error("Failed to get host...")
        exit(-1)

    def get_ip(self) -> str:
        resp = self.get(self.host + f"/srun_portal_pc", headers=headers).text
        try:
            ip = compile(r'((1\d{2}|25[0-5]|2[0-4]\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)').search(
                resp).group()
        except AttributeError:
            self.logger.error("Failed to get IP")
            ip = self.get_ip()
        return ip

    def get_token(self) -> str:
        callback = f"jQuery1124015280105355320628_{round(time() * 1000)}"
        params = {
            "callback": callback,
            "username": self.username,
            "ip": self.get_ip(),
            "_": round(time() * 1000)
        }
        resp = self.get(self.host + "/cgi-bin/get_challenge", headers=headers, params=params).text.strip(
            callback + "()")
        self.logger.debug(resp)
        token = loads(resp)["challenge"]
        self.logger.info(f"Token: {token}")
        return token

    def get_info(self) -> str:
        return "{SRBX1}" + b64encode(xencode(dumps({
            "username": self.username,
            "password": self.password,
            "ip": self.get_ip(),
            "acid": str(self.acid),
            "enc_ver": self.enc_ver,
        }), self.token))

    def get_checksum(self) -> str:
        checksum = self.token + self.username
        checksum += self.token + md5(self.password, self.token)
        checksum += self.token + str(self.acid)
        checksum += self.token + self.get_ip()
        checksum += self.token + self.n
        checksum += self.token + self.vtype
        checksum += self.token + self.info
        return sha1(checksum.encode()).hexdigest()

    def login(self) -> dict:
        self.token = self.get_token()
        self.info = self.get_info()
        self.checksum = self.get_checksum()
        callback = f"jQuery1124015280105355320628_{round(time() * 1000)}"
        device = choice(devices)
        params = {
            "callback": callback,
            "action": "login",
            "username": self.username,
            "password": "{MD5}" + md5(self.password, self.token),
            'os': device[0],
            'name': device[1],
            "double_stack": "0",
            "chksum": self.checksum,
            "info": self.info,
            "ac_id": str(self.acid),
            "ip": self.get_ip(),
            "n": self.n,
            "type": self.vtype,
            "_": round(time() * 1000)
        }
        resp = self.get(self.host + "/cgi-bin/srun_portal", headers=headers, params=params).text
        result: dict = loads(resp.strip(callback + "()"))
        self.logger.debug(result)
        if result.get("suc_msg"):
            self.logger.success(f'login: {result["suc_msg"]} {self.username} {result.get("online_ip")}')
        else:
            self.logger.error(f'{result.get("error")}: {result.get("error_msg")}')
            if "BAS" in result.get("error_msg") or "Nas" in result.get("error_msg"):
                """
                INFO failed, BAS respond timeout.
                Nas type not found.
                """
                self.logger.error("ac_id error, retry in 5 seconds...")
                self.acid += 1
                sleep(5)
                result = self.login()
            elif "E2901" in result.get("error_msg"):
                """
                E2901: (Third party -200)ldap_first_entry error
                E2901: (Third party 1)bind_user2: ldap_bind error
                """
                self.logger.error("username or password error...")
                result["error_msg"] = "4xx"
            elif "E2606" in result.get("error_msg"):
                """
                E2606: User is disabled.
                """
                self.logger.error("user is disabled...")
                result["error_msg"] = "4xx"
        return result

    def logout(self) -> dict:
        callback = f"jQuery112405185119642573086_{round(time() * 1000)}"
        t = round(time())
        status = self.check()
        username = status.get("user_name") if status.get("user_name") else self.username
        ip = status.get("online_ip") if status.get("online_ip") else self.get_ip()
        params = {
            "callback": callback,
            "username": username,
            "ip": ip,
            "time": t,
            "unbind": "1",
            "sign": sha1(f"{t}{username}{ip}1{t}".encode()).hexdigest(),
            "_": round(time() * 1000)
        }
        resp = self.get(self.host + "/cgi-bin/rad_user_dm", headers=headers, params=params).text
        result: dict = loads(resp.strip(callback + "()"))
        self.logger.debug(result)
        self.logger.info(f'logout: {result.get("error")}')
        return result

    def check(self) -> dict:
        callback = f"jQuery112405185119642573086_{round(time() * 1000)}"
        params = {
            "callback": callback,
            "_": round(time() * 1000)
        }
        resp = self.get(self.host + "/cgi-bin/rad_user_info", headers=headers, params=params).text
        result: dict = loads(resp.strip(callback + "()"))
        self.logger.debug(result)
        self.logger.info(f'check: {result.get("error")}')
        return result


def refresh():
    logger.debug("Try to refresh...")
    manager = Manager(*get_random_auth())
    manager.logout()
    retry_login(manager)


def check():
    logger.debug("Check status...")
    manager = Manager()
    status = manager.check()
    if status.get("error") != "ok":
        logger.warning(f"{status.get('error')}, try to login...")
        retry_login(manager, refresh_auth_before_login=True)


def get_random_auth():
    auth = choice(auths)
    return auth["username"], auth["password"]


def set_random_auth(manager: Manager):
    manager.username, manager.password = get_random_auth()


def retry_login(manager: Manager, refresh_auth_before_login: bool = False):
    while True:
        if refresh_auth_before_login:
            set_random_auth(manager)
        result = manager.login()
        if result.get("error_msg") != INVALID_AUTH_ERROR:
            return result
        if not refresh_auth_before_login:
            set_random_auth(manager)
        logger.debug(f"username or password is incorrect, retry in {RETRY_DELAY} seconds...")
        sleep(RETRY_DELAY)


def setup_logger():
    logger.remove()
    logger.add(
        "srun_login.log", rotation="10 MB", level="DEBUG",
        format="<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>srun_login</u></c> | {message}"
    )
    logger.add(
        stdout, level="INFO",
        format="<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>srun_login</u></c> | {message}"
    )


def load_auths():
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as file:
            return load(file)
    except Exception as e:
        logger.bind(module="srun_login").error(f"{e}, please check {AUTH_FILE}")
        exit(-1)


def start_scheduler():
    scheduler = BlockingScheduler()
    scheduler.add_job(refresh, 'interval', hours=6)
    scheduler.add_job(check, 'interval', minutes=2, next_run_time=datetime.now())
    logger.info("Process started")
    scheduler.start()


def main():
    global auths
    setup_logger()
    auths = load_auths()
    start_scheduler()


if __name__ == "__main__":
    main()
