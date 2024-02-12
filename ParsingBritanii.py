from typing import List, Dict
from playwright.sync_api import sync_playwright,BrowserContext,ElementHandle
import pandas as pd


def Lusina(context:BrowserContext):
    ParsingBritanii = context.new_page()
    ParsingBritanii.goto("https://british-bakery.ru/catalog/svezhaya-vypechka-i-sendvichi/")
    button = ParsingBritanii.query_selector("body > main > div.pagination-container > div.pagination-lazy > a")
    button.click()
    names_selector = "div > div.product-list-item-data > a"
    prices_selector = "div > div.product-list-item-controls > div > div.product-list-item-data-price.list-desktop-price > span"

    if names:=ParsingBritanii.query_selector_all(names_selector):
        names:List[ElementHandle] = [i.evaluate('node => node.innerText') for i in names ]
    if prices:=ParsingBritanii.query_selector_all(prices_selector):
        prices:List[ElementHandle] = [i.evaluate('node => node.innerText') for i in prices]
    names.remove("Круассан с миндальным кремом")
    return {'names':names, 'prices':prices}


def Tomurchella():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False,slow_mo=1800)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            is_mobile=False,
            java_script_enabled=True
        )


        data = Lusina(context)
        print(pd.DataFrame(data))


if __name__ ==  "__main__":
    Tomurchella()