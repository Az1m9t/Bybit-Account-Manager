import asyncio
import logging

import requests
from DrissionPage import Chromium, ChromiumOptions
from session_handler import SessionHandler
from encryption_service import EncryptionService
from captcha_solver import CaptchaSolver
from google2fa import OtpAuth
import uuid
from os import urandom
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoginService:
    def __init__(self, username, password, proxy, captcha_api_key, base32secret3232=None):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.captcha_solver = CaptchaSolver(captcha_api_key)
        self.base32secret3232 = base32secret3232
        self.session_handler = SessionHandler()
        self.session = self.session_handler.session
        self.login_name = str(uuid.uuid4())

        self.tr_id = urandom(16).hex()


    def get_last_two_numbers(self, input_string):
        # Находим все последовательности чисел в строке
        numbers = re.findall(r'\d+', input_string)

        # Если найдено меньше двух чисел, возвращаем ошибку или пустой список
        if len(numbers) < 2:
            return "Недостаточно чисел в строке"

        # Возвращаем последние два числа
        return numbers[-2:]
    async def login(self):
        try:
            co = ChromiumOptions().headless()
            browser = Chromium(co)
            tab = browser.get_tab()
            logger.info("Opening login page...")
            tab.get("https://www.bybit.com/en/login")
            for cookie in browser.cookies():
                self.session.cookies.set(cookie['name'], cookie['value'])
            logger.info("Cookies retrieved and added to session.")
            browser.quit()
            logger.info(self.session.cookies)
            logger.info("Initial GET request successful. Cookies obtained.")
            cookies = self.session.cookies.get_dict()

            self.session.headers.update({'Guid': self.login_name})
            json_data = {
                'login_name': self.login_name,
                'txid': '',
                'scene': '31000',
                'country_code': '',
            }

            logger.info("Sending POST request to order CAPTCHA...")
            post_response = self.session.post(
                'https://api2.bybit.com/user/magpice/v1/captcha/order',
                json=json_data,
                cookies=cookies,
                timeout=10
            )

            post_response.raise_for_status()
            logger.info("POST request for CAPTCHA order successful.")
            captcha_response = post_response.json()

            if captcha_response['ret_code'] == 0:
                challenge_data = captcha_response['result']
                logger.info("Received CAPTCHA challenge data.")

                gt4_solution = await self.captcha_solver.solve_captcha_with_retry(challenge_data, retries=3)

                if gt4_solution:
                    cap_data = {
                        'lot_number': gt4_solution.lot_number,
                        'captcha_output': gt4_solution.captcha_output,
                        'pass_token': gt4_solution.pass_token,
                        'gee4test_gen_time': gt4_solution.gen_time,
                        'login_name': self.login_name,
                        'captcha_type': 'gee4captcha',
                        'serial_no': challenge_data['serial_no'],
                        'scene': '31000',
                    }

                    logger.info("Sending POST request to verify CAPTCHA...")
                    verification_response = self.session.post(
                        'https://api2.bybit.com/user/magpice/v1/captcha/verify',
                        json=cap_data
                    )
                    verification_response_json = verification_response.json()
                    logger.info(f"Verification Response: {verification_response_json}")
                    if verification_response_json.get('ret_msg') == 'success':
                        logger.info("CAPTCHA verification successful.")
                        encrypted_password, timestamp = EncryptionService.encrypt_password(self.password)

                        login_data = {
                            'username': self.username,
                            'magpie_verify_info': {
                                'token': challenge_data['serial_no'],
                                'scene': '31000',
                            },
                            'proto_ver': '2.1',
                            'encrypt_password': encrypted_password,
                            'encrypt_timestamp': timestamp,
                        }

                        logger.info("Sending POST request for login...")
                        req = self.session.get('https://www.bybit.com/en/login')
                        response = self.session.post('https://api2.bybit.com/login', json=login_data)
                        print(f'after-resp-headers: {self.session.headers}')
                        print(f'after-resp-cookie: {self.session.cookies.get_dict()}')
                        print(f'resp-headers: {response.headers}')
                        logger.info(f"Login response status: {response.status_code}, content: {response.content}")
                        risk_token = response.json()['result']['risk_token']
                        print(risk_token)
                        otp_auth = OtpAuth('IUVDCI7EHQ57GHMK')
                        otp_code = await otp_auth.get_otp()
                        google_2fa_data = {
                            "risk_token": f"{risk_token}",
                            "component_list": {
                                "google2fa": f"{otp_code}"
                            }
                        }
                        response1 = self.session.post('https://api2.bybit.com/user/public/risk/verify', json=google_2fa_data)
                        print(response1.text)
                        risk_token = response1.json()['result']['risk_token']
                        print(risk_token)
                        encrypted_password, timestamp = EncryptionService.encrypt_password(self.password)
                        login_data = {
                            "username": f"{self.username}",
                            "magpie_verify_info":
                                {
                                    "token": f"{challenge_data['serial_no']}",
                                    "scene": "31000"
                                },
                            "proto_ver": "2.1",
                            "google2fa": f"{otp_code}",
                            "risk_token": f"{risk_token}",
                            "encrypt_password": f"{encrypted_password}",
                            "encrypt_timestamp": f"{timestamp}"
                        }
                        response = self.session.post('https://api2.bybit.com/login', json=login_data)
                        print(response.json())
                        print(self.session.cookies.get('secure-token'))
                        return self.session.cookies.get('secure-token')
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error occurred: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
