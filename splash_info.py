import aiohttp
import asyncio
from datetime import datetime, timezone

class SplashInfo:
    def __init__(self, session):
        self.session = session

    async def unix_to_datetime(self, unix_timestamp):
        try:
            # Преобразование Unix-времени из миллисекунд в секунды
            unix_timestamp_in_seconds = unix_timestamp / 1000

            # Преобразование Unix-времени в объект datetime с указанием временной зоны UTC
            dt = datetime.fromtimestamp(unix_timestamp_in_seconds, tz=timezone.utc)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (OSError, OverflowError, ValueError) as e:
            # Если значение недопустимо, выводим сообщение об ошибке
            print(f"Ошибка при преобразовании Unix-временного штампа {unix_timestamp}: {e}")
            return None

    async def get_info(self):
        url = 'https://api2.bybit.com/spot/api/deposit-activity/v2/project/ongoing/projectList'
        async with self.session.get(url) as response:
            resp = await response.json()
            print(resp)
            token_info_list = []
            for token in resp['result']:
                print('----------------------------------------------------------------------------------------------------')
                print(f'Name: {token["token"]} - {token["tokenFullName"]}')
                print(f'Link: https://www.bybit.com/en/trade/spot/token-splash/detail?code={token["code"]}')
                print(f'Total Prize Pool: {token["totalPrizePool"]}')
                print(f'Participants: {token["participants"]}')
                if token['taskType'] == 3:
                    old_us = True
                else:
                    old_us = False
                print(f'For Old Users: {old_us}')
                print(token["depositStart"])
                print(f'Action Time: {await self.unix_to_datetime(token["applyStart"])} - {await self.unix_to_datetime(token["applyEnd"])}')
                print(f'Deposit Time: {await self.unix_to_datetime(token["depositStart"])} - {await self.unix_to_datetime(token["depositEnd"])}')

                token_info = {
                    "name": token["tokenFullName"],
                    "link": f'https://www.bybit.com/en/trade/spot/token-splash/detail?code={token["code"]}',
                    "total_prize_pool": token["totalPrizePool"],
                    "participants": token["participants"],
                    "for_old_users": token['taskType'] == 3,
                    "action_time": f'{await self.unix_to_datetime(token["applyStart"])} - {await self.unix_to_datetime(token["applyEnd"])}',
                    "deposit_time": f'{await self.unix_to_datetime(token["depositStart"])} - {await self.unix_to_datetime(token["depositEnd"])}',
                    "icon_link": f'{token["icon"]}',
                }
                token_info_list.append(token_info)
            return token_info_list


