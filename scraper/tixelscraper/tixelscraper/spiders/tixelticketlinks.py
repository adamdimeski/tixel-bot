import scrapy
from ..items import TixelscraperItem
from urllib.parse import urlencode
from scrapy.utils.project import get_project_settings

settings = get_project_settings()
proxy_meta = settings.get("PROXY_META")


class Tixelticketlinks(scrapy.Spider):
    name = 'tixelticketlinks'
    allowed_domains = ['tixel.com']
    def __init__(self, *args, **kwargs):
        super(Tixelticketlinks, self).__init__(*args, **kwargs)
        self.start_url = kwargs.get('start_url')
        self.urls = []
        self.child = False
        self.cat = ""

    def start_requests(self):
        yield scrapy.Request(url=self.start_url, callback=self.parse, meta={"proxy": proxy_meta})
        #yield scrapy.Request(url=self.start_url, callback=self.parse)
        #yield scrapy.Request(url=get_proxy_url(self.start_url), callback=self.parse, meta=meta)

    def parse(self, response):
        links_cats = response.xpath('//a[contains(@href, "http://tixel.com/au")]/@href').getall()
        links_tickets= response.xpath('//a[contains(@href, "https://tixel.com/t/")]/@href').getall()
        links_prices= response.xpath('//button[contains(@data-e2e, "components/buttons/event/buy-ticket")]//span/text()').getall()
        #links_tickets_prices= response.xpath('//a[contains(@href, "https://tixel.com/t/")]/@href | //button[contains(@data-e2e, "components/buttons/event/buy-ticket")]//span[not[contains(@class, "text-sm")]]/text()').getall()
        for link in links_cats:
            self.urls.append(link)

        filtered_prices = [x for x in links_prices if not x == "/ea"]
        for i, link in enumerate(links_tickets):
            item = TixelscraperItem()
            if self.child:
                item['category'] = self.cat
            else:
                item['category'] = 'Unknown'
            item['url'] = link

            if filtered_prices[i] is None:
                print("Price is a None value.")
                raise ValueError

            try:
                item['price'] = filtered_prices[i]
            except IndexError:
                print("Price list does not match ticket list")
            except:
                print("error getting prices for tickets")
            yield item


        if len(self.urls) > 0:
            self.child = True
            next_url = self.urls.pop(0)
            self.cat = next_url.split("/")[-1]
            yield scrapy.Request(url=next_url, callback=self.parse, meta={"proxy": proxy_meta})
            #yield scrapy.Request(url=next_url, callback=self.parse)
            #next_url = get_proxy_url(self.urls.pop(0))
            #yield scrapy.Request(url=next_url, callback=self.parse, meta=meta)
