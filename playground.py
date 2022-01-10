import os
import requests
import json
import smtplib
from newsapi import NewsApiClient
import pandas
from email.message import EmailMessage

STOCK = "AAPL"
COMPANY_NAME = "Apple Inc"
ALPHA_API_KEY = os.environ.get("STOCK_API_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASS = os.environ.get("SENDER_PASS")
RECIPIENT_EMAIL = os.environ.get("SENDER_EMAIL")
# Add your email smtp server and port
SMTP_SERVER = ("smtp.gmail.com", 465)


# https://app.mailgun.com/app/dashboard
# https://newsapi.org/docs/endpoints/top-headlines

# First request Stock data
def request_stock_data(stock_name):
    parameters = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': stock_name,
        'apikey': ALPHA_API_KEY
    }
    url = f'https://www.alphavantage.co/query'
    r = requests.get(url, params=parameters)
    data = r.json()
    with open(f'{stock_name}_stock.json', 'w') as daily_stock:
        json.dump(data, daily_stock, indent=4)
    with open(f'{stock_name}_stock.json', 'r') as daily_stock:
        read_data = json.load(daily_stock)
        return read_data["Time Series (Daily)"]


# Second compare between the close price for yesterday and day before yesterday
def close_stock_price(stock_data: dict) -> float:
    stock_daily_data = pandas.DataFrame(stock_data)
    dates = stock_daily_data.columns
    yesterday_close = float(stock_daily_data.loc['4. close', dates[1]])
    before_yesterday = float(stock_daily_data.loc['4. close', dates[2]])
    return round(before_yesterday - yesterday_close, 2)


# Third Check if the price increase/drop by 5% if so request news

def request_news_data(search_word, data):
    news = []
    new_data = {}
    news_api = NewsApiClient(NEWS_API_KEY)
    stock_daily_data = pandas.DataFrame(data)
    dates = stock_daily_data.columns
    news_data = news_api.get_everything(q=f'{search_word}', language='en', page=1, page_size=5,
                                        from_param=f"{dates[0]}")
    news_number = 1
    for title in news_data['articles'][:3]:
        new_data = {
            f"{search_word}_{news_number}": {
                'title': title['title'],
                'Brief': title['description']}
        }
        news.append(new_data)
        news_number += 1
        if os.path.isfile(f'news_{search_word}.json'):
            with open(f'news_{search_word}.json', 'r') as news_file:
                read_data_news = json.load(news_file)
                read_data_news.update(new_data)
            with open(f'news_{search_word}.json', 'w') as news_file:
                json.dump(read_data_news, news_file, indent=4)
        else:
            with open(f'news_{search_word}.json', 'w') as news_file:
                json.dump(news[0], news_file, indent=4)
    with open(f'news_{search_word}.json', 'r') as news_file:
        read_data_news = json.load(news_file)
        return read_data_news


# Fourth create a message to be sent.
def create_message(company_name, stock_value, news_data_file):
    with open('news_template.txt', 'r') as news_file:
        news_template = news_file.read()
        new_data = news_template
        new_data = new_data.replace("[COMPANY_NAME]", company_name)
        new_data = new_data.replace("[STOCK_STATUS]", stock_value)
        news_data_frame = pandas.DataFrame(news_data_file)
        news_list = news_data_frame.columns
        new_data = new_data.replace("[HEADLINE]", news_data_frame.loc['title', news_list[0]])
        new_data = new_data.replace("[BRIEF]", news_data_frame.loc['Brief', news_list[0]])
        print(new_data)
    with open(f"{company_name}_news.txt", 'w', encoding="utf-8") as news_file:
        news_file.write(new_data)
    with open(f"{company_name}_news.txt", 'r', encoding="utf-8") as news_file:
        message_data = news_file.read()
        return message_data


# Fifth step send an email using http to smtp to use pythonanywhere
def send_stock_email(subject, content):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.set_content(content)
    with smtplib.SMTP_SSL(SMTP_SERVER[0], SMTP_SERVER[1]) as connection:
        connection.login(SENDER_EMAIL, SENDER_PASS)
        connection.send_message(msg)
        print("Message sent")


# main function will combines all function to create and send the message:
def stock_alert_app(stock, company_name):
    # Step 1 request stock data
    data = request_stock_data(stock)
    # Step 2 compare between yesterday close and day before yesterday
    stock_price = close_stock_price(data)
    # Step 3 Check if price increase or drop between 5% and in both request news
    # load first day on stock daily
    news_data = request_news_data(company_name, data)
    if stock_price <= -0.05:
        stock_percentage = '🔻' + str(stock_price) + '%'
        # create a message
        content_msg = create_message(company_name, stock_percentage, news_data)
        send_stock_email(f"{company_name} Stock status", content_msg)
    elif stock_price >= 0.05:
        stock_percentage = '🔺' + str(stock_price) + '%'
        content_msg = create_message(company_name, stock_percentage, news_data)
        send_stock_email(f"{company_name} Stock status", content_msg)


stock_alert_app(STOCK, COMPANY_NAME)
