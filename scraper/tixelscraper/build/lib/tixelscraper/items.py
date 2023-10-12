# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TixelscraperItem(scrapy.Item):
    url = scrapy.Field()
    category = scrapy.Field()
    price = scrapy.Field()
    ticketID = scrapy.Field()
    eventName = scrapy.Field()
    eventDate = scrapy.Field()
    time = scrapy.Field()
