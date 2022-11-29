import scrapy


class Tixelticketlinks(scrapy.Spider):
    name = 'tixelticketlinks'
    allowed_domains = ['tixel.com']
    def __init__(self, *args, **kwargs):
        super(Tixelticketlinks, self).__init__(*args, **kwargs)
        self.start_urls = kwargs.get('start_urls').split(',')

    def parse(self, response):
        links_cats = response.xpath('//a[contains(@href, "http://tixel.com/au")]/@href').getall()
        links_tickets= response.xpath('//a[contains(@href, "https://tixel.com/t/")]/@href').getall()
        for link in links_cats:
            cat = link.split("/")[-1]
            yield{
                'type' : 'category',
                'category' : cat,
                'url' : link,
            }
        for link in links_tickets:
            yield{
                'type' : 'ticket',
                'url' : link,
            }
