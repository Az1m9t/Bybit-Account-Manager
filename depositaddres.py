import aiohttp
import asyncio

class BybitAPI:
    def __init__(self, coin: str, chain: str, session: aiohttp.ClientSession):
        # print(session.headers, session.cookie_jar)
        self.base_url = "https://api2.bybit.com/v3/private/cht/asset-deposit/deposit/address-chain"
        self.coin = coin
        self.chain = chain
        self.session = session
        # print(self.session.headers)
        # for cookie in session.cookie_jar:
        #     print(cookie.key, ":", cookie.value)

    async def get_deposit_address(self):
        """Отправка запроса на получение адреса депозита"""
        chain_list = {
            "ERC20":"ETH", "TRC20":"TRX", "Arbitrum One":"ARBI", "SOL":"SOL", "BSC (BEP20)":"BSC", "Polygon PoS":"MATIC", "OP Mainnet":"OP", "AVAXC":"CAVAX", "Mantle Network":"MANTLE", "KAVAEVM":"KAVAEVM", "CELO":"CELO", "TON":"TON"
        }
        params = {
            "coin": self.coin,
            "chain": chain_list[self.chain]
        }  # Генерация строки прокси
        print(params)

        async with self.session.get(self.base_url, params=params) as response:
            response.raise_for_status()  # Проверка на ошибки HTTP
            resp = await response.json()
            try:
                return resp['result']['address'], resp['result']['tag']
            except Exception as e:
                return resp['ret_msg'], resp['ret_msg']

