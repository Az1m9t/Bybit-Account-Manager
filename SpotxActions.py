import aiohttp


class Actions:
    def __init__(self, session, type):
        self.session = session
        self.type = type

    async def main(self):
        # Выбор URL в зависимости от типа
        if self.type == 'splash':
            url = 'https://api2.bybit.com/spot/api/deposit-activity/v2/project/ongoing/projectList'
        else:
            url = 'https://api2.bybit.com/spot/api/airdrop-splash/v1/project/list?pageSize=20&pageNo=1&requestCategory=2'

        # Выполнение GET-запроса с использованием сессии
        async with self.session.get(url) as resp:
            # Ожидание получения полного ответа
            response_text = await resp.json()
        print(response_text)
        event_list=[]
        if self.type == 'splash':
            for event in response_text['result']:
                event_list.append(event['prizeToken'])
        else:
            pass
        return event_list  # Возврат ответа, если это нужно
