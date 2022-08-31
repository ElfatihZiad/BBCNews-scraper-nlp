#!/usr/bin/env python
# coding: utf-8


import requests
from bs4 import BeautifulSoup as bs
import pymongo
#import logging

client = pymongo.MongoClient('mongo',27017)
db = client['bbcnews']
collection = db['links']

def parse_sitemap(url):
    
    response = requests.get(url)

    if response.status_code != 200:
        return None

    xml_as_str = response.text

    soup = bs(xml_as_str, "lxml")

    records = []
    loc_elements = soup.find_all("url")
    for loc in loc_elements:
        if ('www.bbc.com/news/' in loc.loc.text) and (loc.lastmod.text > '2022-05-24T14:54:50Z'):
            collection.insert_one(dict({'lastmod': loc.lastmod.text, 'url': loc.loc.text}))
    
    #fieldnames = ['lastmod','url']
    #with open(output_file, 'a', encoding='utf8', newline='') as f:
    #    fc = csv.DictWriter(f, fieldnames=fieldnames)
    #    fc.writeheader()
    #    fc.writerows(records)

    print(f'Found {len(records)} links')

archive_sitemaps_url = 'https://www.bbc.com/sitemaps/https-index-com-archive.xml'
response = requests.get(archive_sitemaps_url)
soup = bs(response.text, "lxml")
sitemaps_links = []
loc_elements1 = soup.find_all("loc")
for loc in loc_elements1:
    sitemaps_links.append(loc.text)


for i in range(85, len(sitemaps_links)+1):
    print(f'collecting Archive number {i} from total of {len(sitemaps_links)} ')
    URL = f'https://www.bbc.com/sitemaps/https-sitemap-com-archive-{i}.xml'
    parse_sitemap(URL)
    print(f'Archive {i} Collected')

print('All Archived articles were collected')