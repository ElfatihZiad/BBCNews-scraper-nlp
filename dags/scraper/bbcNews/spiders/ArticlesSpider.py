import scrapy
from bbcNews.items import BbcnewsItem
from pymongo import MongoClient
import json
class NewsSpider(scrapy.Spider):
    name = "NewsSpider"

    #db = MongoClient('mongo',27017) #you can add db-url and port as parameter to MongoClient(), localhost by default
    #start_urls = db.bbcnews.links.distinct('url') #use appropriate finding criteria here according to the structure of data resides in that collection

    def __init__(self, docs_count=None, *args, **kwargs):
        super(NewsSpider, self).__init__(*args, **kwargs)
        client = MongoClient('mongo',27017)  #you can add db-url and port as parameter to MongoClient(), localhost by default
        db = client.bbcnews
        self.start_urls = [c['url'] for c in db.links.find().sort('lastmod',-1).limit(500)] # change to int(docs_count)


    def parse(self, response):    

        item = BbcnewsItem()   

        item['url'] = response.url
        item['date'] =  response.css('time::attr(datetime)').get()
        item['menu_submenu'] = '-'.join(response.url.replace('https://www.bbc.com/news/', '').split("-")[:-1]) # get the main substring after /new/ in the url
        item['title'] = response.xpath('//*[@id="main-heading"]/text()').get()
        item['subtitle'] = response.xpath('//p/b/text()').get()
        item['authors'] = response.xpath('//strong/text()').getall()
        item['text'] = ' '.join(response.css('p::text').getall()[:-1])  # joining paragraphs
        item['topic_name'] = response.xpath('//*[@id="main-content"]/div[5]/div/div[1]/article/section/div/div[2]/ul/li/a/text()').getall()
        item['topic_url'] = response.xpath('//*[@id="main-content"]/div[5]/div/div[1]/article/section/div/div[2]/ul/li/a/@href').getall()
        item['images'] = response.css('img').xpath('@src').getall()
        
        return item

        #fieldnames ={'response_status','article_link','title','subtitle','authors','date','images','text','topic_name','topic_url'}

        #with open('articles_data.csv', 'a', encoding='utf8', newline='') as f:
        #    fc = csv.DictWriter(f, fieldnames=fieldnames)
        #    fc.writeheader()
        #    fc.writerows(item)


