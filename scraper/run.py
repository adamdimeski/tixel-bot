import sys
import getopt
import time
import os
import signal
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import date
import requests
import json
import uuid
from bson import json_util


with open('./details.json') as file:
    details = json.load(file)

uri = details['mongodb_uri']
# Create a new client and connect to the server
# Send a ping to confirm a successful connection
starturl = ''
update_frequency = 600
unique_id = uuid.uuid4()


def getOrders(url, db):
    collection = db["orders"]
    orders = list(collection.find({"url": url}))
    return orders


def getTickets(url, db):
    collection = db["tickets"]
    tickets = list(collection.find({"eventName": urlDecodable(url)["name"]}))
    return tickets


def logScrape(url, db, tickets):
    collection = db["scraper-log"]
    prices = list()
    for ticket in tickets:
        prices.append(ticket['price'])
    record = {'eventName': urlDecodable(
        url)["name"], 'time': datetime.now(), 'prices': prices, 'uuid': str(unique_id)}

    collection.insert_one(record)
    return tickets


def deleteTickets(url, db):
    collection = db["tickets"]
    return collection.delete_many({"url": url})


def deleteOrders(url, db):
    collection = db["orders"]
    return collection.delete_many({"url": url})


def assessOrder(tickets, orders, db):
    prices = list()
    collection = db["tickets"]
    for order in orders:
        prices.append(order["threshold"])
    matched = list()
    for ticket in tickets:
        if ticket["price"] <= max(prices):
            matched.append(ticket)
    return matched


def handler(signum, frame):
    exit(1)


def run_scrapy(url):
    os.system("scrapy crawl tixelticketlinks -a start_url=" + url)
    pass


def urlDecodable(url) -> dict:
    segments = url.split('/')
    data = dict()
    if "2023" in segments:
        yearI = segments.index('2023')  # || segments.index('2023')
        data["expiry"] = date(int(segments[yearI]), int(
            segments[yearI + 1]), int(segments[yearI + 2]))
        data["year"] = "2023"
    elif "2024" in segments:
        yearI = segments.index('2024')  # || segments.index('2023')
        data["expiry"] = date(int(segments[yearI]), int(
            segments[yearI + 1]), int(segments[yearI + 2]))
        data["year"] = "2024"
    else:
        data["expiry"] = date(2023, 12, 12)
        data["year"] = "2023"

    data["name"] = segments[-1]
    return data


def main(argv):

   os.chdir("./tixelscraper")
   opts, args = getopt.getopt(argv, "s:f:", ["starturl=", "frequency="])
   for opt, arg in opts:
     if opt in ("-s", "--starturl"):
         starturl = arg
     elif opt in ("-f", "--frequency"):
         frequency = arg
   client = MongoClient(uri, server_api=ServerApi('1'))
   try:
       update_frequency = int(frequency) * 60
   except:
       print("Invalid frequency argument")
       exit()
   print(starturl)

   try:
       urlDecodable(starturl)
   except Exception as e:
       print(e)
       print("Invalid url argument")
       exit()

   try:
       client.admin.command('ping')
       db = client["tixelscrapy"]
       print("Pinged your deployment. You successfully connected to MongoDB!")
   except Exception as e:
       print(e)
       exit()

   # run_scrapy(starturl)
   while True:
       run_scrapy(starturl)
       orders = getOrders(starturl, db)

       if len(orders) == 0:
           print("exiting")
           deleteTickets(starturl, db)
           signal.signal(signal.SIGINT, handler)
           exit()
       expiryDate = "2005-01-01"
       newUpdateFrequency = update_frequency
       for order in orders:
           print(order['expiry'])
           print(datetime.strptime(order['expiry'], '%Y-%m-%d'))
           if datetime.strptime(order['expiry'], '%Y-%m-%d').date() > datetime.strptime(expiryDate, '%Y-%m-%d').date():
               expiryDate = order['expiry']
           if (int(order['frequency']) * 60) < newUpdateFrequency:
               newUpdateFrequency = int(order['frequency']) * 60
       update_frequency = newUpdateFrequency

       if datetime.now().date() > datetime.strptime(expiryDate, '%Y-%m-%d').date():
           print("exiting")
           deleteTickets(starturl, db)
           deleteOrders(starturl, db)
           signal.signal(signal.SIGINT, handler)
           exit()

       tickets = getTickets(starturl, db)
       matched = assessOrder(tickets, orders, db)
       payload = json.dumps(matched, default=str)
       matched = sorted(matched,
                        key=lambda d: d['price'], reverse=True)[:5]
       if len(matched) > 0:
           print("Found matched tickets")
           try:
               headers = {"Content-Type": "application/json"}
               r = requests.post('http://host.docker.internal:8090/ticketEvent',
                                 data=payload, headers=headers)
               if r.status_code == 200:
                   print("POST request successful!")
               else:
                   print(
                       f"POST request failed with status code {r.status_code}")
           except:
               print("Error sending ticket update post request")

       # do logging
       logScrape(starturl, db, tickets)
       print("Now waiting ...")

       time.sleep(update_frequency)


signal.signal(signal.SIGINT, handler)

if __name__ == "__main__":
    main(sys.argv[1:],)


# Find the name of the event and date and figure out if it is valid
# return error if it isn't.


# pymongo
