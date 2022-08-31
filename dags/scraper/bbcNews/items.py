# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

#from itemadapter import ItemAdapter

class BbcnewsItem(scrapy.Item):
    
    url = scrapy.Field()
    date = scrapy.Field()
    link = scrapy.Field()
    menu_submenu = scrapy.Field()
    title = scrapy.Field()
    subtitle = scrapy.Field()
    authors = scrapy.Field()
    text = scrapy.Field()
    topic_name = scrapy.Field()
    topic_url = scrapy.Field()
    images = scrapy.Field()

