from scrapy.exceptions import IgnoreRequest
#import logging
import pymongo


class IgnoreDupReqMiddleware(object):

    def __init__(self):
        self.client = pymongo.MongoClient('mongo',27017)
        self.db = self.client['bbcnews']

    def process_request(self, request, spider):
        url = request.url
        if self.db[spider.name].find_one({"url": url}):
            print(f'ignore duplicated url: {url}')
            raise IgnoreRequest()
