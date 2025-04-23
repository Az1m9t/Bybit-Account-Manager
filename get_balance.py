import aiohttp
import asyncio


class GetBalance():
    def __init__(self, direction, session):
        self.direction = direction
        self.session = session
    async def send_request(self):
        url1 = "https://api2.bybit.com/fiat/private/fund-account/balance-list?account_category=crypto"
        url2 = "https://api2.bybit.com/siteapi/unified/private/account-walletbalance"
        coin_list = {}
        if self.direction == 'fund':
            async with self.session.get(url1) as response:
                print("Status:", response.status)
                resp = await response.json()
                # print("Response:", resp)
            for coin in resp['result']:
                if coin['totalBalance'] != '0':
                    print(f'{coin["currency"]} - {coin["totalBalance"]}')
                    coin_list[coin["currency"]] = coin["totalBalance"]
        else:
            async with self.session.post(url2) as response:
                print("Status:", response.status)
                resp = await response.json()
                # print("Response:", resp)
            for coin in resp['result']['coinList']:
                if coin['wb'] != '' and coin['wb'] != '0':
                    print(f'{coin["coin"]} - {coin["wb"]}')
                    coin_list[coin["coin"]] = coin["wb"]
        return coin_list

