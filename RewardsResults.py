import aiohttp
import asyncio

class GetResult:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session

    async def get_result(self):
        status, result = await self.get_uuid()
        if status == 1:
            url1 = 'https://api2.bybit.com/segw/awar/v1/awarding/search-together'
            url2 = 'https://api2.bybit.com/fht/growth/award-plus-srv/v1/user_reward_statistics'
            data1 = {
                "pagination": {
                    "pageNum": 1,
                    "pageSize": 12
                },
                "filter":
                    {
                    "awardType": "AWARD_TYPE_UNKNOWN",
                    "newOrderWay": True,
                    "rewardBusinessLine": "REWARD_BUSINESS_LINE_DEFAULT",
                    "rewardStatus": "REWARD_STATUS_DEFAULT",
                    "getFirstAwardings": False,
                    "simpleField": True,
                    "allow_amount_multiple": True,
                    "return_reward_packet": True,
                    "return_transfer_award": True
                }
            }
            data2 = {"userId": result}
            rewards_list = {}
            async with self.session.post(url1, json=data1) as response:
                resp = await response.json()
                print(resp)
                try:
                    for reward in resp['result']['awardings']:
                        coin = reward['award_detail']['coin']
                        amount = reward['award_detail']['award_title']
                        rewards_list[coin] = amount
                except Exception as e:
                    return str(e), str(e)
            async with self.session.post(url2, json=data2) as response:
                resp = await response.json()
                print(resp)
                try:
                    cnt = resp['result']['res']['awardTotalNum']
                    amount = resp['result']['res']['amountSum']
                    return rewards_list, f'{cnt} rewards = {float(amount):.3f}$'
                except Exception as e:
                    return str(e), str(e)
        else:
            return result, result


    async def get_uuid(self):
        url = 'https://api2.bybit.com/v2/private/user/profile'
        async with self.session.get(url) as response:
            resp = await response.json()
            print(resp)
            try:
                return 1, resp['result']['id']
            except Exception as e:
                return -1, str(e)
