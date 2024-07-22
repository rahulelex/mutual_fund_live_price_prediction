"""
This module Update the data. Fetch all links of mutual funds. Fetch all the stocks
holding of each mutual fund.
"""
import logging
import time
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


class ScrapData():
    """
    This class is responsible for Scraping data from website.
    """
    def __init__(self):
        self.logger= None
        self.configure_logging()

    def configure_logging(self):
        """
        Configure logging and formatting.
        """
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def fetch_urls(self, page_url: str) -> list:
        """
        Fetch URLs of mutual funds from a given page URL
        """
        try:
            page = requests.get(page_url, timeout=30)
            soup = BeautifulSoup(page.text, 'html.parser')
            rows = soup.find_all('a', attrs={'class': 'pos-rel f22Link'})
            urls = [f"https://groww.in{row.get('href')}" for row in rows]
            return urls
        except Exception as error:
            print(f"Error fetching URLs: {error}")
            return []

    def save_urls_to_file(self, urls: list, filename: str) -> bool:
        """
        Save URLs to a file
        """
        try:
            print("Saving urls to file")
            with open(filename, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(f"{url}\n")
            print("Save urls Success")
            return True
        except Exception as error:
            print(f"Error saving URLs to file: {error}")
            return False

    def fetch_and_save_urls(self) -> bool:
        """
        Fetch and save all mutual funds URLs.
        """
        try:
            self.logger.info("Starting fetch page urls")
            all_urls = []
            for page_number in range(1, 96):
                page_url = f"https://groww.in/mutual-funds/filter?q=&fundSize=&investType=%5B%22SIP%22%5D&pageNo={page_number}&sortBy=3"
                urls_on_page = self.fetch_urls(page_url)
                all_urls.extend(urls_on_page)
            print("All urls fetched")

            if not all_urls:
                print("No URLs fetched.")
                return False
            return self.save_urls_to_file(all_urls, "data_files/mutual_funds_links.txt")

        except Exception as error:
            print(f"ERROR: {error}")
            return False

    def fetch_funds_holdings(self) -> None:
        """
        Fetch all mutual funds holdings.
        """
        self.logger.info("Initiating fetching All fund holdings.")
        self.logger.info("This may take a long time, up to 1 Hour 10 Minutes.".center(100, "*"))
        start_time = datetime.now()
        self.logger.info(start_time)

        try:
            driver = self.initialize_driver()
            urls = self.read_urls_from_file()

            all_funds = []

            for row_num, url in enumerate(urls):
                if not url:
                    self.logger.debug("empty URL")
                    continue

                self.logger.debug(row_num)
                self.logger.debug(url)
                driver.get(url.strip())
                self.logger.debug("CHECK")

                try:
                    self.click_see_all(driver)
                except TimeoutException:
                    self.logger.debug("Either 'See All' not present or unable to click")

                self.scroll_to_load_content(driver)

                fund_data = self.extract_fund_data(driver)
                if fund_data:
                    all_funds.append(fund_data)

            self.save_to_json(all_funds)

            self.logger.info("Write finish")
            stop_time = datetime.now()
            self.logger.info(stop_time - start_time)

        except Exception as error:
            self.logger.error(f"ERROR: {error}")

        finally:
            self.close_driver(driver)

    def initialize_driver(self):
        """
        Initialise driver.
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )
        return driver

    def read_urls_from_file(self):
        """
        Read all urls from file.
        """
        with open('data_files/mutual_funds_links.txt', 'r', encoding='utf-8') as f:
            urls = f.read().split('\n')
        return urls

    def click_see_all(self, driver):
        """
        Click on See all to view all stock holdings.
        """
        element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(
            (By.XPATH, '//*[@id="holdings101Container"]/div/div/div/div')))
        element.click()

    def scroll_to_load_content(self, driver):
        """
        Scroll to load full content on page.
        """
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def extract_fund_data(self, driver):
        """
        Extract holding of a mutual fund.
        """
        page = driver.page_source
        soup = BeautifulSoup(page, 'html.parser')
        scheme_name = soup.find('h1', class_='mfh239SchemeName displaySmall')
        if not scheme_name:
            return None

        scheme_name = scheme_name.text.strip()

        table = soup.find('table', class_='tb10Table holdings101Table')
        if not table:
            return None

        stocks = table.find_all('tr', class_='holdings101Row')
        fund_holdings = []

        for stock in stocks:
            stock_name_element = stock.find('div', class_='pc543Links')
            holding_percent_element = stock.find('td', string=lambda text: text and '%' in text)
            if stock_name_element and holding_percent_element:
                stock_name = stock_name_element.text.strip()
                holding_percent = holding_percent_element.text.strip().replace('%', '')
                link = stock.find('a', class_='contentPrimary')['href']
                fund_holdings.append(
                    {'stock_name': stock_name, 'holding_percent': holding_percent, 'stock_url': link})

        return {'schemeName': scheme_name, 'holdings': fund_holdings}

    def save_to_json(self, data):
        """
        Save data to a json file.
        """
        file_path = 'data_files/mutual_funds_data.json'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    def close_driver(self, driver):
        """
        Close driver.
        """
        driver.quit()


def main():
    """
    Main function to update database.
    """
    scrap= ScrapData()
    # if scrap.fetch_and_save_urls():
    #     scrap.fetch_funds_holdings()
    scrap.fetch_funds_holdings()


if __name__ == "__main__":
    main()
