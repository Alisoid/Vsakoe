import os
from typing import List
import re

from playwright.async_api import async_playwright, BrowserContext, ElementHandle, Page

from asyncio import run, gather, sleep

import pandas as pd

from utils import LOG


def keep_numbers(value: str) -> int:
    value = re.sub(r'\D+', '', value)
    return int(value.strip())


async def Lusina(context: BrowserContext, categories: List[str]):
    result = []

    # Цикл по каждой категории
    for category in categories:
        LOG.opt(colors=True).debug(f'Сбор данных по категории: <m>{category}</m>')
        # Создание страницы для категории
        # TODO: сделать асихнронным парсинг категорий
        ParsingBritanii: Page = await context.new_page()
        await ParsingBritanii.goto(category, wait_until='domcontentloaded')
        button = await ParsingBritanii.query_selector("body > main > div.pagination-container > div.pagination-lazy > a")
        # Оффсет для всех товаров на странице
        while button:
            await button.click()
            await sleep(0.3)
            LOG.debug('Открыта новая страница')
            button = await ParsingBritanii.query_selector("body > main > div.pagination-container > div.pagination-lazy > a")

        names_selector = "div > div.product-list-item-data > a"
        prices_selector = "div > div.product-list-item-controls > div > div.product-list-item-data-price.list-desktop-price > span"

        if names := await ParsingBritanii.query_selector_all(names_selector):
            links: List[str | ElementHandle] = ['https://british-bakery.ru' + await element.get_attribute("href") for element in names]
            names: List[str | ElementHandle] = [await i.evaluate('node => node.innerText') for i in names]
        if prices := await ParsingBritanii.query_selector_all(prices_selector):
            prices: List[int | ElementHandle] = [keep_numbers(await i.evaluate('node => node.innerText')) for i in prices]

        async def parse_description(link):
            LOG.opt(colors=True).debug(f'Сбор описания <m>{link}</m>')
            item_page: Page = await context.new_page()
            await item_page.goto(link, wait_until='domcontentloaded')
            btn = await item_page.query_selector("div.product-info-section.flexbox > div.product-info-box > div.tabset > ul > li:nth-child(2) > a")
            await btn.click()
            description = await item_page.query_selector("div.product-info-section.flexbox > div.product-info-box > div.tabset > div > div.tab.active")
            description = await description.inner_text()
            await item_page.close()
            return description

        # Значение батча устанавливать на своё усмотрение, не рекоммендуется больше 25.
        batch: int = 25 if len(links) > 25 else len(links)

        all_descriptions = []

        for i in range(0, len(links), batch):
            descriptions = [parse_description(i) for i in links[i:i+batch]]
            descriptions = await gather(*descriptions)
            all_descriptions.extend(descriptions)

        result.append(pd.DataFrame({
            'name': names,
            'price': prices,
            'link': links,
            'description': all_descriptions
        }))
        await ParsingBritanii.close()
    LOG.success('Данные успешно собраны')
    return result


async def Tomurchella(categories_links: List[str]):
    # Запуск браузера
    async with async_playwright() as playwright:
        # WARN: headless=True не работает, дом контент не загружается
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            no_viewport=False,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            bypass_csp=True,
            is_mobile=False,
            java_script_enabled=True
        )
        LOG.debug('Контекст создан')

        data = await Lusina(context, categories_links)
        df: pd.DataFrame = pd.concat(data)
        fp = os.getcwd() + '/data/ParsingBritanii.xlsx'
        df.to_excel(fp, index=False)
        LOG.debug(f'Файл сохранен по адресу {fp}')


if __name__ == "__main__":
    # Сюда можно вставить ссылку на категорию через запятую
    run(Tomurchella([
        # "https://british-bakery.ru/catalog/torty/",
        "https://british-bakery.ru/catalog/svezhaya-vypechka-i-sendvichi/",
    ]))
