import asyncio
import logging

import login_service_2fa
import login_service1
import login_service
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Login:
    def __init__(self, username, password, proxy, captcha_api_key, otp, base32secret3232=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.captcha_api_key = captcha_api_key
        self.otp = otp
        self.base32secret3232 = base32secret3232

    async def start_login(self):
        logger.info("Starting login process...")
        if self.otp:
            login_serv = login_service.LoginService(self.username, self.password, self.proxy, self.captcha_api_key, self.base32secret3232)
        else:
            login_serv = login_service1.LoginService(self.username, self.password, self.captcha_api_key)
        secret_token = await login_serv.login()
        logger.info("Login process finished.")
        return secret_token, self.proxy


USERNAME = 'TEST@gmail.com'
PASSWORD = 'TEST'
PROXY = '123123'
CAPTCHA_API_KEY = "827yr934u8r3j9h94hf94hf934ijf4"
OTP = True
if OTP:
    base32secret3232 = 'URYGFUEYRHUFHREY'
else:
    base32secret3232 = None

async def main():
    logger.info("Starting login process...")
    login_service = Login(USERNAME, PASSWORD, PROXY, CAPTCHA_API_KEY, OTP, base32secret3232)
    token = await login_service.start_login()
    print(token)
    logger.info("Login process finished.")

if __name__ == "__main__":
    asyncio.run(main())
