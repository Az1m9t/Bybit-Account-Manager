import aiohttp
import asyncio


class Transfer():
    def __init__(self, direction, sum, session, coin):
        self.direction = direction
        self.sum = sum
        self.session = session
        self.coin = coin

    async def send_request(self):
        url1 = "https://api2.bybit.com/v3/private/asset/query-account-list?accountListDirection=to&sortRule=default"
        url2 = "https://api2.bybit.com/v3/private/asset/transfer"


        async with self.session.get(url1) as response:
            print("Status:", response.status)
            resp = await response.json()
            print("Response:", resp)
        if resp['result']['items'][0]['accountType'] == 'ACCOUNT_TYPE_FUND':
            fund_code = resp['result']['items'][0]['accountId']
            unified_code = resp['result']['items'][1]['accountId']
        else:
            fund_code = resp['result']['items'][1]['accountId']
            unified_code = resp['result']['items'][0]['accountId']
        print(self.direction)
        if self.direction == 'fund_to_unified':
            payload2 = {
                "amount": f"{self.sum}",
                "fromAccountType": "ACCOUNT_TYPE_FUND",
                "from_account_id": f"{fund_code}",
                "sCoin": f"{self.coin}",
                "toAccountType": "ACCOUNT_TYPE_UNIFIED",
                "to_account_id": f"{unified_code}"
            }
        else:
            payload2 = {
                "amount": f"{self.sum}",
                "fromAccountType": "ACCOUNT_TYPE_UNIFIED",
                "from_account_id": f"{unified_code}",
                "sCoin": f"{self.coin}",
                "toAccountType": "ACCOUNT_TYPE_FUND",
                "to_account_id": f"{fund_code}"
            }
        async with self.session.post(url2, json=payload2) as response:
            print(payload2)
            print("Status:", response.status)
            resp = await response.json()
            print("Response:", resp)
            if resp['ret_msg'] != "success":
                print(resp['ret_msg'])
            else:
                print('success')

