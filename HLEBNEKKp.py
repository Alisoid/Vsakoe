import os
from typing import List, Dict
import re
import json
from asyncio import run, gather, Semaphore

from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from aiohttp import ClientSession

import pandas as pd
import numpy as np

from utils import LOG


class XlebParser:

    __domain: str = 'https://www.xleb.ru'
    __headers: Dict[str, str] = {
        'accept': '*/*',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
    }
    _store_part_id: int | None = None

    async def parse(self) -> pd.DataFrame:
        async with ClientSession(
            self.__domain,
            headers=self.__headers
        ) as session:
            self._store_part_id: int = await self._get_store_part_id(session)
            LOG.debug(f'Store part id: {self._store_part_id}')
            catalog: List[Dict] = await self._parse_catalog(session)
            LOG.debug('Данные каталога получены.')
            df = pd.json_normalize(catalog, record_path='products', meta='slice')
            # Данные цены, описания находятся в поле текст
            df['text'] = df['text'].apply(self.parse_item_description)
            # Deprecated
            # items: List[int] = [product['uid'] for item in catalog for product in item['products']][:3]
            # items: List[Dict] = await self._parse_items(session, items)
            return df

    async def _get_store_part_id(self, session: ClientSession):
        async with session.get('/catalog') as resp:
            text = await resp.text()
            soup = BeautifulSoup(text, features='lxml')
            values = list(map(self.search_store_part, soup.find_all('script')))
            return list(filter(lambda x: x is not None, values))[0]

    async def _parse_catalog(
        self,
        session: ClientSession,
        limit: int = 24
    ) -> List[Dict]:
        session._base_url = None

        params: Dict = {
            'storepartuid': self._store_part_id,
            'recid': '690538402',
            'c': '1729802470548',
            'getparts': 'true',
            'getoptions': 'true',
            'slice': '1',
            'size': limit,
        }
        resp: List[Dict] = await self._get_product_list(session, params)
        total: int = resp['total']

        if total <= limit:
            return resp

        data: List[Dict] = []

        pages: int = int(np.ceil(total / limit))

        for page in range(2, pages + 1):
            data.append(self._get_product_list(session, params, page))

        result = await gather(*data)
        result.append(resp)

        return result

    async def _get_product_list(
        self,
        session: ClientSession,
        params: Dict,
        page: int = 1
    ) -> List[Dict]:
        url: str = 'https://store.tildaapi.com/api/getproductslist/'
        params.update({'slice': page})

        async with session.get(url, params=params) as resp:
            return json.loads(await resp.text())

    # Deprecated
    async def _parse_items(self, session: ClientSession, items: List[str]):
        sem = Semaphore(3)

        async def fetch_with_semaphore(id_):
            LOG.debug(f'Сбор данных {id_}')
            async with sem:
                return await self.get_item(session, id_)

        data = []

        for id_ in items:
            data.append(fetch_with_semaphore(id_))

        result = await gather(*data)
        LOG.success('Данные успешно собраны')
        for item in result:
            item['data'] = await self.parse_item_description(item['data'])

        return result

    # Deprecated
    async def get_item(self, session: ClientSession, id_: int) -> str:
        url: str = urljoin('https://www.xleb.ru/catalog/tproduct/', str(id_))
        async with session.get(url) as resp:
            return {'id': id_, 'data': await resp.text()}

    def parse_item_description(self, text: str) -> List[Dict] | str:
        soup = BeautifulSoup(text, features='lxml')
        text = ' '.join(soup.stripped_strings)
        # TODO add description parser
        # if 'Состав' in text:
        #     energy_value = text
        # attributes = [{
        #     'ingredients': soup.find_all('span')[1].text.split(','),
        #     'energy value': self.keep_numbers(soup.find_all('span')[2].text),
        #     'proteins': self.keep_numbers(soup.find_all('span')[3].text),
        #     'fats': self.keep_numbers(soup.find_all('span')[4].text),
        #     'carbohydrates': self.keep_numbers(soup.find_all('span')[5].text),
        #     'prices': [{
        #         i.text.split('/')[0]: self.keep_numbers(i.text.split('/')[1])
        #     } for i in soup.find_all('strong')[1:]],
        # }]
        # return attributes
        return text


    @staticmethod
    def search_store_part(value: Tag) -> int | None:
        pattern = r"var options=\{storepart:'(.*?)'"
        match = re.search(pattern, value.text)
        if match:
            return match.group(1)

    @staticmethod
    def keep_numbers(value: str, type_: int | float = float) -> float:
        if ',' in value:
            value = value.replace(',', '.')
        value = re.sub(r'[^0-9.,]+', '', value)
        # return type_(value.strip())
        return value.strip()


if __name__ == '__main__':
    df = run(XlebParser().parse())
    fp = os.getcwd() + '/data/catalog.xlsx'
    LOG.debug(f'Файл сохранен по адресу {fp}')
    df.to_excel(fp, index=False)
    print(df)
