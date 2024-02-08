from typing import List, Dict
from playwright.sync_api import sync_playwright, BrowserContext, Page
import pandas as pd
import numpy as np


def parce(context: BrowserContext) -> Dict:
    page: Page = context.new_page()

    page.goto('https://www.xleb.ru')

    name_selector: str = 'div > div > div > div.card-body > h3 > a'
    volume_selector: str = 'div > div > div > div.card-body > span'
    price_selector: str = 'div > div > div > div.card-footer > a > span'

    if names := page.query_selector_all(name_selector):
        names: List = [i.evaluate('node => node.innerText') for i in names]
    if valumes := page.query_selector_all(volume_selector):
        valumes: List = [i.evaluate('node => node.innerText') for i in valumes]
    if prices := page.query_selector_all(price_selector):
        prices: List = [i.evaluate('node => node.innerText') for i in prices]

    return {'name': names, 'volume': valumes, 'price': prices}


def transfrom(data) -> pd.DataFrame:
    df = pd.DataFrame(data)

    df[['volume', 'volume_type']] = df['volume'].str.extract(r'(\d+) (\w+)')
    df['price'] = df['price'].replace(r'\D+', '', regex=True)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['is_soldout'] = np.where(df['price'].isna(), 'Раскупили', 'В наличии')
    df = df[['name', 'volume', 'volume_type', 'price', 'is_soldout']]
    df.columns = [
        'Наименование',
        'Объем',
        'Ед. измерения',
        'Цена',
        'Есть в продаже'
    ]
    return df


def load(data: pd.DataFrame) -> None:
    data.to_excel('D:/Work/workflow/.temp/parced_hlebnik.xlsx', index=False)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            is_mobile=False,
            java_script_enabled=True
        )
        data: Dict = parce(context)
        context.close()

    table = transfrom(data)
    load(table)


if __name__ == '__main__':
    main()

