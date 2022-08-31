# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
#from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
from scrapy import signals
from scrapy.exporters import CsvItemExporter
import pymongo
import logging


class DropIfEmptyFieldPipeline(object):

    def process_item(self, item, spider):

        # test if only "title" is empty,
        if not(item["title"]):
            raise DropItem()
        else:
            return item


#class BbcnewsPipeline:
#    def process_item(self, item, spider):
#        return item



class DuplicatesPipeline:

    def __init__(self):
        self.urls_seen = set()

    def process_item(self, item, spider):

        if item['_id'] in self.urls_seen:
            raise DropItem("Duplicate item found: %s" % item)
        else:
            self.urls_seen.add(item['_id'])
            return item
    
    

class MongoPipeline(object):

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient('mongo',27017)
        self.db = self.client[self.mongo_db]
        self.db['spider.name'].create_index("url", unique=True)

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        #exists = self.db[spider.name].find_one({"url": dict(item)["url"]})
        #if not exists:
        self.db[spider.name].insert_one(dict(item))
        logging.debug("Article added to MongoDB")
        return item

class CSVPipeline(object):

  def __init__(self):
    self.files = {}

  @classmethod
  def from_crawler(cls, crawler):
    pipeline = cls()
    crawler.signals.connect(pipeline.spider_opened, signals.spider_opened)
    crawler.signals.connect(pipeline.spider_closed, signals.spider_closed)
    return pipeline

  def spider_opened(self, spider):
    file = open('%s_items.csv' % spider.name, 'a+b')
    self.files[spider] = file
    self.exporter = CsvItemExporter(file)
    self.exporter.fields_to_export = ['date','link','menu_submenu','title','subtitle','authors','text','topic_name','topic_url','images']
    self.exporter.start_exporting()

  def spider_closed(self, spider):
    self.exporter.finish_exporting()
    file = self.files.pop(spider)
    file.close()

  def process_item(self, item, spider):
    self.exporter.export_item(item)
    return item


