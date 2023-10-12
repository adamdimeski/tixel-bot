# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from scrapy.utils.project import get_project_settings
import time
import datetime
import pymongo
#check for duplicates
#remove tickets that are no longer found on Website
#

settings = get_project_settings()


class TixelscraperPipeline:
    def process_item(self, item, spider):
        return item

class DuplicatesPipeline:
    def __init__(self):
        self.tickets_seen = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        if adapter['url'] in self.tickets_seen:
            raise DropItem(f"Duplicate item found: {item!r}")
        else:
            self.tickets_seen.add(adapter['url'])
            return item

class PricePipeline:

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        try:
            segmented_price = adapter['price'].split("$")
            item['price'] = float(segmented_price[1])
        except:
            print("Error converting price to number")
        return item

class addTicketIdPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        ticket_segments = adapter["url"].split("/")
        if ticket_segments[0] != "https:" or ticket_segments[1] != "" \
        or ticket_segments[2] != "tixel.com" or ticket_segments[3] != "t" \
        or ticket_segments[4] == None:
            raise DropItem(f"Incorrect ticket format found: {item!r}")
        else:
            try:
                item["ticketID"] = ticket_segments[4]
                return item
            except:
                print("Error getting ticket ID")

class MetadataPipeline:

    #Get the event name
    #Get the event date
    #get the current time
    def __init__(self):
        self.time = int(time.time())

    def open_spider(self, spider):
        segmented_url = spider.start_url.split("/")
        try:
            self.eventName = segmented_url[-1]
            day = int(segmented_url[-2])
            month = int(segmented_url[-3])
            year = int(segmented_url[-4])
            self.eventDate = datetime.date(year, month, day)
        except:
            print ("Error extracting event name and date information")
        # ISO 8601 date format

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        item['time'] = self.time
        item['eventName'] = self.eventName
        item['eventDate'] = str(self.eventDate.isoformat())

        return item

class MongoPipeline:

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = settings.get("MONGODB_URI")
        self.mongo_db = settings.get("MONGODB_DATABASE")
        self.batch_time = 0
        self.eventName = None
        self.eventDate = None
        self.collection_name = "tickets"

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE', 'items')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

    def close_spider(self, spider):
        #remove tickets of the same type eventName and eventDate and not the current bach_time
        query = {"eventName": self.eventName, "eventDate": self.eventDate, "time": { "$lt": self.batch_time}}
        self.db[self.collection_name].delete_many(query)
        self.client.close()

    def process_item(self, item, spider):
        if not self.eventName:
            self.batch_time = item['time']
            self.eventName = item['eventName']
            self.eventDate = item['eventDate']
        #update ticket if already exists and update it instead
        self.db[self.collection_name].update_one({"ticketID" : item["ticketID"]}, {"$set": ItemAdapter(item).asdict()}, upsert=True)
        return item
