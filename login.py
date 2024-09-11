from hashlib import sha1
from json import loads, dumps, load
from random import choice
from re import compile
from sys import stdout
from time import time, sleep

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from requests import Session

from utils.base import b64encode
from utils.device import devices
from utils.hash import md5
from utils.xencode import xencode

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 "
                  " Safari/537.36 Edg/128.0.0.0"
}


class Manager(Session):
    
    def __init__(self, username: str, password: str):
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
    
    def get_host(self):
        hosts = ["https://login.hdu.edu.cn", "https://portal.hdu.edu.cn"]
        for i in hosts:
            try:
                self.get(i)
                return i
            except Exception as e:
                self.logger.info(f"Host {i} {e}")
        self.logger.error("Failed to get host...")
        exit(1)
    
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
            self.logger.success(f'login: {result["suc_msg"]}')
        else:
            self.logger.error(f'{result.get("error")}: {result.get("error_msg")}')
            if "BAS" in result.get("error_msg") or "Nas" in result.get("error_msg"):
                self.logger.error("ac_id error, retry in 5 seconds...")
                self.acid += 1
            sleep(5)
            result = self.login()
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
    logger.info("Try to refresh...")
    try:
        auths = load(open("auth.json", "r", encoding="utf-8"))
        auth = choice(auths)
        manager = Manager(auth["username"], auth["password"])
        manager.logout()
        sleep(2)
        manager.login()
    except Exception as e:
        logger.bind(module="srun_login").error(f"{e}, please check auth.json")


def check():
    logger.info("Check status...")
    try:
        auths = load(open("auth.json", "r", encoding="utf-8"))
        auth = choice(auths)
        manager = Manager(auth["username"], auth["password"])
        status = manager.check()
        if status.get("error") != "ok":
            logger.warning(f"{status.get('error')}, try to login...")
            manager.login()
    except Exception as e:
        logger.bind(module="srun_login").error(f"{e}, please check auth.json")


def main():
    logger.remove()
    logger.add(
        "srun_login.log", rotation="10 MB", level="DEBUG",
        format="<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>srun_login</u></c> | {message}"
    )
    logger.add(
        stdout, level="INFO",
        format="<g>{time:MM-DD HH:mm:ss}</g> [<lvl>{level}</lvl>] <c><u>srun_login</u></c> | {message}"
    )
    scheduler = BlockingScheduler()
    scheduler.add_job(refresh, 'interval', hours=12)
    scheduler.add_job(check, 'interval', minutes=5)
    logger.info("Process started")
    scheduler.start()


if __name__ == "__main__":
    main()
