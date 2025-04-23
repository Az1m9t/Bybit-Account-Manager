import asyncio
import logging
import asyncio
import random
import numpy as np
import aiohttp
import cv2
import re
from playwright.async_api import async_playwright
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


async def load_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read()


class LoginService:
    response_received_event = asyncio.Event()
    responses = []
    response_processed_urls = set()
    response_processed = False

    target_urls = [
        # "https://api2.bybit.com/user/magpice/v1/captcha/verify",
        "https://api2.bybit.com/login",
        "https://api2.bybit.com/user/public/risk/verify"
    ]

    def __init__(self, username, password, proxy, captcha_api_key, base32secret3232=None, background=None,
                 puzzle_piece=None, debugger=True):
        self.username = username
        self.password = password
        self.proxy = proxy
        self.captcha_solver = CaptchaSolver(captcha_api_key)
        self.base32secret3232 = base32secret3232
        self.session_handler = SessionHandler()
        self.session = self.session_handler.session
        self.login_name = str(uuid.uuid4())
        self.debugger = debugger
        self.tr_id = urandom(16).hex()

    def _read_image(self, image_source):
        """
        Read an image from a file or a requests response object.
        """
        if isinstance(image_source, bytes):
            return cv2.imdecode(np.frombuffer(image_source, np.uint8), cv2.IMREAD_ANYCOLOR)
        else:
            raise TypeError("Invalid image source type. Must be bytes.")

    def get_last_two_numbers(self, input_string):
        # Находим все последовательности чисел в строке
        numbers = re.findall(r'\d+', input_string)

        # Если найдено меньше двух чисел, возвращаем ошибку или пустой список
        if len(numbers) < 2:
            return "Недостаточно чисел в строке"

        # Возвращаем последние два числа
        return numbers[-2:]


    def find_puzzle_piece_position(self, background, puzzle_piece):
        """
        Find the matching position of a puzzle piece in a background image.
        """
        background = self._read_image(background)
        puzzle_piece = self._read_image(puzzle_piece)
        # Apply edge detection
        edge_puzzle_piece = cv2.Canny(puzzle_piece, 100, 200)
        edge_background = cv2.Canny(background, 100, 200)

        # Convert to RGB for visualization
        edge_puzzle_piece_rgb = cv2.cvtColor(edge_puzzle_piece, cv2.COLOR_GRAY2RGB)
        edge_background_rgb = cv2.cvtColor(edge_background, cv2.COLOR_GRAY2RGB)

        # Template matching
        res = cv2.matchTemplate(edge_background_rgb, edge_puzzle_piece_rgb, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        top_left = max_loc
        h, w = edge_puzzle_piece.shape[:2]
        bottom_right = (top_left[0] + w, top_left[1] + h)

        # Calculate required values
        center_x = top_left[0] + w // 4
        center_y = top_left[1] + h // 2
        position_from_left = center_x
        position_from_bottom = background.shape[0] - center_y

        # Draw rectangle, lines, and coordinates if debugger is True
        if self.debugger:
            cv2.imwrite('input.png', background)
            cv2.rectangle(background, top_left, bottom_right, (0, 0, 255), 2)
            cv2.line(background, (center_x, 0), (center_x, edge_background_rgb.shape[0]), (0, 255, 0), 2)
            cv2.line(background, (0, center_y), (edge_background_rgb.shape[1], center_y), (0, 255, 0), 2)
            cv2.imwrite('output.png', background)

        return {
            "position_from_left": position_from_left,
            "position_from_bottom": position_from_bottom,
            "coordinates": [center_x, center_y]
        }

    @staticmethod
    async def handle_response(response):
        """
        Асинхронный обработчик ответа с сервера.

        Parameters:
        ----------
        response : Response
            Объект ответа, который перехватывается с сервера.
        """
        # Проверяем, находится ли URL в списке целевых URL и не обработан ли он ранее
        if any(target_url in response.url for target_url in
               LoginService.target_urls) and response.url not in LoginService.response_processed_urls:
            try:
                # Читаем тело ответа (может быть текстовым или JSON)
                response_body = await response.json()
                response_headers = response.headers


                # Добавляем ответ в глобальный список для последующей печати
                LoginService.responses.append({
                    "url": response.url,
                    "body": response_body,
                    "headers": response_headers
                })

                # Добавляем URL в список уже обработанных, чтобы не обрабатывать его повторно
                LoginService.response_processed_urls.add(response.url)

                # Устанавливаем событие, чтобы сообщить, что ответ получен
                LoginService.response_received_event.set()

            except Exception as e:
                print(f"Ошибка при обработке ответа: {e}")

    async def login(self):
        try:
            p = await async_playwright().start()
            browser = await p.chromium.launch(
                headless=False,
                proxy={"server": "socks5://AEtLHBkB:u6hwT1CQ@45.195.175.246:63881"}  # Прокси для Playwright (SOCKS5 или HTTP)
            )

            context = await browser.new_context()
            page = await context.new_page()
            # Добавляем обработчик для перехвата ответа с определенного URL
            page.on("response", lambda response: asyncio.create_task(LoginService.handle_response(response)))

            await page.goto("https://httpbin.org/ip")
            cookies = await context.cookies()
            print(cookies)
            self.session.headers.update({'Guid': self.login_name})
            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])

            await page.fill(
                'xpath=//*[@id="uniframe-cht-login"]/div[2]/div/div[1]/div/div/div[2]/div/div/div/form/div[1]/div/div[1]/input',
                'wieuhfihweg@gmail.com')
            await page.fill(
                'xpath=//*[@id="uniframe-cht-login"]/div[2]/div/div[1]/div/div/div[2]/div/div/div/form/div[2]/div/div/input',
                'pkdOIFqwDW@#^%^&$#8326753hf')
            await page.click(
                'xpath=//*[@id="uniframe-cht-login"]/div[2]/div/div[1]/div/div/div[2]/div/div/div/form/button')
            cookies = await context.cookies()
            print(cookies)
            while True:
                try:
                    cpat = await page.query_selector(
                        "xpath=//div[contains(@class, 'geetest_box_wrap') and contains(@style, 'display: block')]")
                    break
                except Exception as e:
                    print(e)
                    pass
            await asyncio.sleep(5)
            while True:
                try:
                    bg_list = await page.query_selector_all("xpath=//div[contains(@class, 'geetest_bg')]")
                    slice_list = await page.query_selector_all("xpath=//div[contains(@class, 'geetest_slice_bg')]")

                    if len(bg_list) > 1:
                        canvases = [bg_list[1], slice_list[1]]
                    else:
                        canvases = [bg_list[0], slice_list[0]]

                    images = []
                    for canvas in canvases:
                        style = await canvas.get_attribute('style')
                        url_match = re.search(r'url\("?(.*?)"?\)', style)
                        if url_match:
                            images.append(url_match.group(1))

                    result = self.find_puzzle_piece_position(await load_image(images[0]), await load_image(images[1]))

                    slider_bt = await page.query_selector_all("xpath=//div[contains(@class, 'geetest_btn')]")
                    if len(slider_bt) > 1:
                        slider = slider_bt[1]
                    else:
                        slider = slider_bt[0]
                    slider_bounding_box = await slider.bounding_box()
                    start_x = slider_bounding_box['x'] + slider_bounding_box['width'] / 2
                    start_y = slider_bounding_box['y'] + slider_bounding_box['height'] / 2

                    await page.mouse.move(start_x, start_y)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    target_x = start_x + result['position_from_left'] - 20
                    await page.mouse.move(target_x, start_y, steps=1)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                    await page.mouse.up()
                    await LoginService.response_received_event.wait()
                    # Печать всех перехваченных ответов
                    # for response in GeeTestIdentifier.responses:
                    if LoginService.responses[0]['body']['ret_msg'] == 'success':
                        print(f"URL: {LoginService.responses[0]['url']}")
                        print(f"Тело ответа: {LoginService.responses[0]['body']}")
                        print(f"Полный ответ: {LoginService.responses[0]['header']}")
                        logger.info("CAPTCHA verification successful.")

                        await asyncio.sleep(5)
                        cookies = await context.cookies()
                        print(cookies)
                        self.session.headers.update({'Guid': self.login_name})
                        for cookie in cookies:
                            self.session.cookies.set(cookie['name'], cookie['value'])
                        print(self.session.headers)
                        print(self.session.cookies)
                        await context.close()
                        await browser.close()
                        await p.stop()
                        print('browser is closed')
                        encrypted_password, timestamp = EncryptionService.encrypt_password(self.password)

                        login_data = {
                            'username': self.username,
                            'magpie_verify_info': {
                                'token': LoginService.responses[0]['body']['result']['token'],
                                'scene': '31000',
                            },
                            'proto_ver': '2.1',
                            'encrypt_password': encrypted_password,
                            'encrypt_timestamp': timestamp,
                        }

                        logger.info("Sending POST request for login...")
                        print(self.session.cookies)
                        req = self.session.get('https://www.bybit.com/en/login')
                        print(self.session.cookies)
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
                        response1 = self.session.post('https://api2.bybit.com/user/public/risk/verify',
                                                      json=google_2fa_data)
                        print(response1.text)
                        risk_token = response1.json()['result']['risk_token']
                        print(risk_token)
                        encrypted_password, timestamp = EncryptionService.encrypt_password(self.password)
                        login_data = {
                            "username": f"{self.username}",
                            "magpie_verify_info":
                                {
                                    "token": f"{LoginService.responses[0]['body']['result']['token']}",
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
                except Exception as e:
                    print(e)
                    pass
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error occurred: {e}")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
