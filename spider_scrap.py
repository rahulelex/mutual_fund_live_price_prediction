import json
from bs4 import BeautifulSoup
import re
import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MutualFundsSpider(scrapy.Spider):
    name = 'mutual_funds'

    def __init__(self, fund_name, holdings):
        self.fund_data= {'schemeName': fund_name, 'holdings': holdings}
        self.write_data= {'schemeName': fund_name, 'holdings': []}

        super(MutualFundsSpider, self).__init__()

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )

    def start_requests(self):
        for stock in self.fund_data['holdings']:
            if not stock:
                continue
            url = f"https://groww.in{stock['stock_url']}"
            yield scrapy.Request(url=url, callback=self.parse, meta={'stock': stock})

    def parse(self, response):
        stock = response.meta['stock']
        
        self.driver.get(response.url)
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.lpu38Pri')))
        page = self.driver.page_source

        soup = BeautifulSoup(page, 'html.parser')

        try:
            amount_spans = soup.find_all('span', class_='lpu38Pri', style='overflow: hidden; display: inline-block; position: relative;')
            amounts = [span.text.strip()[0] for span in amount_spans]
            combined_amount_text = ''.join(amounts)
            amount = re.search(r'\d+\.\d+', combined_amount_text)

            if amount:
                current_price = float(amount.group())
            else:
                raise ValueError("Amount not found.")

            div_tag = soup.find('div', class_='lpu38Day')
            yesterday_price = div_tag.get_text(strip=True)
            matches = re.findall(r'([-+]?)(\d+\.\d+)', yesterday_price)

            if matches:
                operator, value = matches[0]
                if operator == '+':
                    yesterday_price = float(current_price) - float(value)
                elif operator == '-':
                    yesterday_price = float(current_price) + float(value)
                else:
                    yesterday_price = float(current_price)
            else:
                raise ValueError("No matches found.")

            holding = {
                "stock_name": stock["stock_name"],
                "holding_percent": stock["holding_percent"],
                "stock_url": stock["stock_url"],
                "yesterday_price": "{:.2f}".format(yesterday_price),
                "current_price": "{:.2f}".format(float(current_price))
            }
            self.write_data["holdings"].append(holding)

        except Exception as error:
            print(f"{response.url} data could not be added, ERROR: {error}")

    def close(self, reason):
        self.driver.quit()
        with open('data_files/fund_holdings_price.json', 'w') as f:
            json.dump(self.write_data, f, indent=4)
