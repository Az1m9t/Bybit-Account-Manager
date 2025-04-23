import aiohttp
import time
import json
import websocket
import threading
import asyncio
from decimal import Decimal, ROUND_DOWN

class BybitTrader:
    def __init__(self, token, usdt_start_count, is_full_balance, trade_amount, session):
        self.token = token
        self.session = session
        self.usdt_start_count = usdt_start_count
        self.is_full_balance = is_full_balance
        self.trade_amount = trade_amount
        self.price = 0
        self.quantity_count = 10
        self.price_count = 0
        self.determined_quantity_count = None  # Сохранение определенного количества знаков после запятой для количества
        self.determined_price_count = None  # Сохранение определенного количества знаков после запятой для цены
        self.suma = 0  # Переменная, за которой мы будем следить
        self.trade_amount_lock = threading.Lock()
        self.progress_callbacks = []
        self.start_balance_callback = []
        self.finish_balance_callback = []
        self.latest_prices = {"sell": None, "buy": None}

    async def send_subscribe_message(self, ws):
        subscribe_message = {
            "topic": "depth",
            "symbol": f"{self.token}USDT",
            "limit": 10,
            "params": {
                "binary": "true"
            },
            "event": "sub"
        }
        await asyncio.to_thread(ws.send, json.dumps(subscribe_message))

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'data' in data and 'a' in data['data'][0] and 'b' in data['data'][0]:
                sell_orders = data['data'][0]['a']
                buy_orders = data['data'][0]['b']
                updated_prices = {
                    "sell": float(sell_orders[0][0]),
                    "buy": float(buy_orders[0][0])
                }
                self.latest_prices.update(updated_prices)
        except json.JSONDecodeError:
            print(f"Failed to decode message: {message}")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket closed with code: {close_status_code}, message: {close_msg}")

    async def on_open(self, ws):
        print("Connected to WebSocket server")
        await self.send_subscribe_message(ws)
        asyncio.ensure_future(self.send_heartbeat(ws))

    def start_async_on_open(self, ws):
        # Создаем новый event loop и запускаем асинхронную функцию on_open
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.on_open(ws))

    async def send_heartbeat(self, ws):
        while True:
            try:
                ping_message = json.dumps({"ping": int(time.time() * 1000)})
                await asyncio.to_thread(ws.send, ping_message)
                print("Ping sent")
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
                break

    def websocket_thread(self):
        timestamp = int(time.time() * 1000)
        ws = websocket.WebSocketApp(
            f"wss://ws2.bybit.com/spot/ws/quote/v2?timestamp={timestamp}",
            on_open=lambda ws: self.start_async_on_open(ws),
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header=[
                "Host: ws2.bybit.com",
                "Origin: https://ws2.bybit.com",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Sec-WebSocket-Key: JxDPLNeI6ljzDw9I2vK9iw==",
                "Sec-WebSocket-Version: 13",
                "accept-language: en",
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36",
            ]
        )

        ws.run_forever(
            ping_interval=60,
            ping_timeout=10,
            skip_utf8_validation=True
        )

    async def create_order(self, order_type):
        try:
            url = "https://api2-1.bybit.com/spot/api/order/create"

            # Вычисляем цену
            if order_type == "buy":
                price_start = Decimal(self.latest_prices["sell"]) * Decimal("1.005")
            else:
                price_start = Decimal(self.latest_prices["buy"]) * Decimal("0.995")

            if self.determined_price_count is None:
                # Определяем количество знаков после запятой для цены один раз
                price_str = f"{price_start:.10f}"  # Максимальное количество знаков для анализа
                self.determined_price_count = len(price_str.split('.')[1].rstrip('0'))

            price = price_start.quantize(Decimal(f"1.{''.join(['0']*self.determined_price_count)}"), rounding=ROUND_DOWN)

            # Определяем количество USDT
            if order_type == "buy":
                usdt_count = self.usdt_start_count if not self.is_full_balance else Decimal(await self.get_spot_wallet_balance("USDT"))
                # Вычисляем количество
                quantity_start = Decimal(usdt_count) / price
                print(quantity_start)
            else:
                print('sell')
                usdt_count = Decimal(await self.get_spot_wallet_balance(self.token))
                print(usdt_count)
                # Вычисляем количество
                quantity_start = usdt_count
                print(quantity_start)



            if self.determined_quantity_count is None:
                # Определяем количество знаков после запятой для количества один раз
                quantity_str = f"{quantity_start:.10f}"  # Максимальное количество знаков для анализа
                self.determined_quantity_count = len(quantity_str.split('.')[1].rstrip('0'))

            quantity = quantity_start.quantize(Decimal(f"1.{''.join(['0']*self.determined_quantity_count)}"), rounding=ROUND_DOWN)
            print(quantity)
            data = {
                "type": "limit",
                "side": order_type,
                "price": str(price),
                "quantity": str(quantity),
                "symbol_id": f"{self.token}USDT",
                "client_order_id": str(int(time.time() * 1000)),
                "time_in_force": "gtc"
            }
            print(data)
            self.session.headers.update({
                "Content-Type": "application/x-www-form-urlencoded",
            })

            async with self.session.post(url, data=data) as response:
                if response.status == 200:
                    response = await response.json()
                    print(response)
                    # Обработка ошибки precision
                    if response.get("ret_code") == 32104:
                        # Пытаемся уменьшать количество знаков после запятой, пока сервер не примет запрос
                        while response.get("ret_code") == 32104 and self.determined_price_count > 0:
                            self.determined_price_count -= 1
                            price = price_start.quantize(Decimal(f"1.{''.join(['0']*self.determined_price_count)}"), rounding=ROUND_DOWN)
                            print(price)
                            data = {
                                "type": "limit",
                                "side": order_type,
                                "price": str(price),
                                "quantity": str(quantity),
                                "symbol_id": f"{self.token}USDT",
                                "client_order_id": str(int(time.time() * 1000)),
                                "time_in_force": "gtc"
                            }
                            async with self.session.post(url, data=data) as response:
                                if response.status == 200:
                                    response = await response.json()
                                    print(response)
                    if response.get("ret_code") == 32107:
                        # Обрабатываем ошибку 32107, уменьшая количество знаков после запятой до приемлемого уровня
                        while response.get("ret_code") == 32107 and self.determined_quantity_count > 0:
                            self.determined_quantity_count -= 1
                            quantity = quantity_start.quantize(Decimal(f"1.{''.join(['0']*self.determined_quantity_count)}"), rounding=ROUND_DOWN)
                            print(quantity)
                            data = {
                                "type": "limit",
                                "side": order_type,
                                "price": str(price),
                                "quantity": str(quantity),
                                "symbol_id": f"{self.token}USDT",
                                "client_order_id": str(int(time.time() * 1000)),
                                "time_in_force": "gtc"
                            }
                            async with self.session.post(url, data=data) as response:
                                if response.status == 200:
                                    response = await response.json()
                                    print(response)
                    if response.get("ret_code") == 32107:
                        decimal_part = quantity.split('.')[1]
                        self.quantity_count = len(decimal_part)

                        while response.get("ret_code") == 32107:
                            self.quantity_count -= 1
                            print(self.quantity_count)
                            quantity = quantity[:-1]
                            data = (
                                f"type=limit&side={order_type}&price={price}&quantity={quantity}"
                                f"&symbol_id={self.token}USDT&client_order_id={int(time.time() * 1000)}"
                                "&time_in_force=gtc"
                            )
                            async with self.session.post(url, data=data) as response:
                                response = await response.json()

                    if response.get('ret_msg') == 'Insufficient account balance':
                        return response.get('ret_msg')
                    if response.get("ret_code") == 0:
                        amount = float(response['result']['price']) * float(response['result']['origQty'])
                        return 1, response["result"]["orderId"], amount
                    else:
                        return -2, response.get("ret_msg")
                else:
                    raise RuntimeError(f"Failed to create order. Status code: {response.status}")
        except Exception as e:
            print(f"Exception in create_order: {e}")
            return e

    async def cancel_order(self, order_id):
        url = "https://api2.bybit.com/spot/api/order/cancel"

        # Обновляем заголовки для этого запроса
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
        })

        data = f"client_order_id={int(time.time() * 1000)}&order_id={order_id}"

        async with self.session.post(url, data=data) as response:
            if response.status == 200:
                resp = await response.json()
                if resp['ret_code'] == 32004:
                    print(await response.json())
                    return 'Order done'
                else:
                    print(resp)
                    print("Order cancelled successfully:")

            else:
                print(f"Failed to cancel order. Status code: {response.status}")
                print(f'Ошибка при отмене: {response.text}')

    async def get_spot_wallet_balance(self, token_id):
        url = "https://api2.bybit.com/siteapi/unified/private/spot-walletbalance"

        payload = {
            "symbolName": self.token + "USDT",
            "limitPrice": "0.0001"
        }

        self.session.headers.update({
            "Content-Type": "application/json",
        })

        async with self.session.post(url, json=payload) as response:
            if response.status == 200:
                response_data = await response.json()
                if "result" in response_data and "coinList" in response_data["result"]:
                    for coin in response_data["result"]["coinList"]:
                        if coin.get("tokenId") == token_id:
                            return coin.get("walletBalance")
            else:
                print(f"Failed to retrieve spot wallet balance. Status code: {response.status}")
                print(f'Ошибка при получении баланса: {response.text}')

    async def register_events(self):
        print('token:', self.token)
        url1 = 'https://api2.bybit.com/spot/api/deposit-activity/v2/project/ongoing/projectList'
        async with self.session.get(url1) as response:
            resp = await response.json()
            print(resp)
        for token in resp['result']:
            if token['token'] == self.token:
                print(f'token code: {token["code"]}')
                payload = {"projectCode": f"{token['code']}"}
                break
            else:
                print('can not find token code')
        url = 'https://api2.bybit.com/spot/api/deposit-activity/v1/project/pledge'
        async with self.session.post(url, json=payload) as response:
            print(await response.json())

    async def get_trade_history_sum(self):
        url = "https://api2.bybit.com/unified/spot/v5/order/trades"

        self.session.headers.update({
            "Content-Type": "application/json",
        })

        end_time = int(time.time() * 1000)
        start_time = end_time - 2595600000  # 24 hours ago
        payload = {
            "limit": 100,
            "startTime": start_time,
            "endTime": end_time,
            # "specialTradeFrom": "1",
            "baseTokenId": self.token,
            "quoteTokenId": "USDT"
        }

        async with self.session.post(url, json=payload) as response:
            try:
                if response.status == 200:
                    response_data = await response.json()  # Используйте await для получения результата JSON

                    if response_data["retCode"] == 0:
                        trades = response_data["result"]["result"]
                        total_amount = sum(
                            float(trade["amount"])
                            for trade in trades
                            if (trade['baseTokenId'] == self.token and trade['type'] == 'Limit')
                        )
                        print(f"Total amount: {total_amount}")
                        return total_amount
                    else:
                        print(f'Ошибка при получении истории покупок1 : {response_data["retMsg"]}')
                        return response_data["retMsg"]
                else:
                    print(f"Failed to retrieve order trades. Status code: {response.status}")
                    # print(f'Ошибка при получении истории покупок: {await response.text()}')  # Используйте await для получения текста ответа
                    return await response.text()
            except Exception as e:
                print(f'Ошибка при получении истории покупок/: {response_data["retMsg"]}')
                return response_data["retMsg"]

    async def get_trade_history(self, orderId):

        self.session.headers.update({
            "Content-Type": "application/json",
        })

        cancel = await self.cancel_order(orderId)
        if cancel != 'Order done':
            return False
        else:
            print("Order done1")
            return True

    async def find_price_num(self):
        for _ in range(3):
            price = str(self.latest_prices["buy"])
            decimal_part = price.split('.')[1]
            self.price_count = max(self.price_count, len(decimal_part))
            price = str(self.latest_prices["sell"])
            decimal_part = price.split('.')[1]
            self.price_count = max(self.price_count, len(decimal_part))
            # await asyncio.sleep(0.3)

        # Метод для регистрации коллбека
    def register_progress_callback(self, callback):
        self.progress_callbacks.append(callback)

    def register_start_balance_callback(self, callback):
        self.start_balance_callback.append(callback)

    def register_finish_balance_callback(self, callback):
        self.finish_balance_callback.append(callback)

    # Обновление значения trade_amount и вызов коллбеков
    async def set_trade_amount(self, value):
        with self.trade_amount_lock:
            self.suma = value
        for callback in self.progress_callbacks:
            callback(self.suma)

    async def run(self):
        try:
            threading.Thread(target=self.websocket_thread, daemon=True).start()
            while self.latest_prices['sell'] is None or self.latest_prices['buy'] is None:
                print("Waiting for price update...")
                await asyncio.sleep(0.5)
            await self.find_price_num()
            await self.register_events()
            suma = await self.get_trade_history_sum()
            if isinstance(suma, str):
                return suma
            print('suma:', suma)
            # Обновляем значение trade_amount и уведомляем прогресс
            await self.set_trade_amount(suma)
            while suma <= self.trade_amount:
                print('self.trade_amount:', self.trade_amount)
                order_id = await self.create_order("buy")
                print(order_id[1])
                if order_id[0] == -2:
                    return order_id[1]
                is_bought = await self.get_trade_history(order_id[1])
                if is_bought:
                    suma += order_id[2]
                    order_id = await self.create_order("sell")
                    is_sold = await self.get_trade_history(order_id[1])
                    if is_sold:
                        suma += order_id[2]
                    else:
                        while not(is_sold):
                            order_id = await self.create_order("sell")
                            is_sold = await self.get_trade_history(order_id[1])
                        suma += order_id[2]
                print('обновляем значение suma')
                print(suma)
                await self.set_trade_amount(suma)
            await asyncio.sleep(1.1)
            suma_req = await self.get_trade_history_sum()
            await self.set_trade_amount(suma_req)
            print(f'{suma} - {suma_req}')
            print('завершение')
            return 1, self.session
        except Exception as e:
            return e

