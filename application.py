import sys
import json
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QListWidget
from scrapy.crawler import CrawlerProcess
from spider_scrap import MutualFundsSpider

class MutualFundSearch(QWidget):
    def __init__(self, mutual_funds):
        super().__init__()
        self.mutual_funds = mutual_funds
        self.holdings=None
        # Connect the signal to a slot
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Mutual Fund Search')
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type fund name...")
        self.search_box.textChanged.connect(self.searchTextChanged)

        self.funds_list = QListWidget()
        self.funds_list.itemClicked.connect(self.itemClicked)

        layout.addWidget(self.search_box)
        layout.addWidget(self.funds_list)

        self.setLayout(layout)

    def searchTextChanged(self, text):
        self.funds_list.clear()
        for mutual_fund in self.mutual_funds:
            fund_name = mutual_fund['schemeName']
            if text.lower() in fund_name.lower():
                self.funds_list.addItem(fund_name)
                # self.holdings= mutual_fund['holdings']
                

    def itemClicked(self, item):
        selected_fund = item.text()
        selected_fund_data=[mf for mf in self.mutual_funds if mf['schemeName'] == selected_fund]
        self.holdings= selected_fund_data[0]['holdings']
        print(f"{selected_fund=}")
        print("This process can take long upto 5 minutes.".center(100, "*"))
        print(f"Total stocks are {len(self.holdings)}".center(100, "-"))

        process = CrawlerProcess(
            settings={'CONCURRENT_REQUESTS': 10, 'DOWNLOAD_DELAY': 0.5},
            install_root_handler=False
        )
        process.crawl(MutualFundsSpider, fund_name=selected_fund, holdings=self.holdings)
        process.start()

        change= self.predict_fund_price()
        print(change)

    def calculate_stock_change(self, yesterday_price, current_price):
        return ((float(current_price) - float(yesterday_price)) / float(yesterday_price)) * 100
    
    def predict_fund_price(self) -> str:
        """
        Fetch all mutual funds urls
        """
        try:
            # Read mutual fund data from file and preprocess it
            with open('data_files/fund_holdings_price.json', 'r') as file:
                mutual_funds_data = json.load(file)  # data variable was not defined

            # Calculate the overall change in the fund's value
            holdings= mutual_funds_data["holdings"]
            total_change = 0
            for holding in holdings:
                stock_change = self.calculate_stock_change(holding["yesterday_price"], holding["current_price"])
                holding_percent = float(holding["holding_percent"])
                total_change += (stock_change * holding_percent)
            return "{:.2f}".format(total_change/100)
        except json.decoder.JSONDecodeError as e:
            print("JSON Decode Error:", e)
            return None


if __name__ == '__main__':
    try:
        # Read mutual fund data from file and preprocess it
        with open('data_files/mutual_funds_data.json', 'r') as file:
            mutual_funds_data = json.load(file)  # data variable was not defined
    except json.decoder.JSONDecodeError as e:
        print("JSON Decode Error:", e)
        sys.exit(1)  # Exit the program if there's a JSON decoding error

    app = QApplication(sys.argv)
    ex = MutualFundSearch(mutual_funds_data)
    ex.show()
    sys.exit(app.exec_())
