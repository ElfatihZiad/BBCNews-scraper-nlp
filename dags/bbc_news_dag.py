from datetime import datetime
import requests
from bs4 import BeautifulSoup as bs
import pymongo

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator


from scripts.data_preparation import process
from scripts.topic_modeling import model
from scripts.sentiment_analysis import sentiment


BASE_URL = 'https://www.bbc.com/sitemaps/https-index-com-news.xml' # last 48 hours articles are listed here


def parse_sitemap(url, collection):
    
    response = requests.get(url)

    if response.status_code != 200:
        return None

    xml_as_str = response.text
    soup = bs(xml_as_str, "lxml")

    loc_elements = soup.find_all("url")
    for loc in loc_elements:
        if ('www.bbc.com/news/' in loc.loc.text):
            try:
                collection.insert_one(dict({'lastmod': loc.lastmod.text, 'url': loc.loc.text}))
                # insert into new collection
            except pymongo.errors.DuplicateKeyError:
                # skip document because it already exists in the collection
                continue


def get_urls_from_sitemap(url):

    client = pymongo.MongoClient('mongo',27017)
    db = client['bbcnews']
    collection = db['links']
    db['NewsSpider'].create_index("url", unique=True)
    response = requests.get(url)
    soup = bs(response.text, "lxml")
    url_list = []
    loc_elements1 = soup.find_all("loc")
    for loc in loc_elements1:
        url_list.append(loc.text)


    for url in url_list:
        parse_sitemap(url, collection)

    print('All links of news articles were collected')

def get_docs_count():
    client = pymongo.MongoClient('mongo',27017)
    db = client['bbcnews']
    links_count = db['links'].count_documents({})
    articles_count = db['NewsSpider'].count_documents({})
    #last_doc = list(collection.find().skip(collection.count_documents({}) - 1))[0]
    print(f'number of links before crawling is {links_count} \n number of articles before crawling is {articles_count}')
    return {'links_count': links_count, 'articles_count': articles_count}
    

default_args = {
    "owner": "airflow",
    #"start_date": days_ago(1),
    "start_date":datetime(2022, 8, 28, 1, 40),
    "depends_on_past": False,
    "retries": 1,
}

dag = DAG(
    'ScrapingDag',
    schedule_interval = '*/30 * * * *',
    catchup=False,
    render_template_as_native_obj=True,
    default_args=default_args
    )


#with scraper_workflow:

t1=PythonOperator(
    task_id="get_docs_count",
    python_callable=get_docs_count,
    dag=dag,        
)

t2 = PythonOperator(
    task_id="get_urls",
    python_callable=get_urls_from_sitemap,
    op_kwargs=dict(
        url=BASE_URL,
    ),
    dag=dag,
)

t3 = BashOperator(
    task_id='crawl',
    bash_command='cd /opt/airflow/dags/scraper && scrapy crawl NewsSpider -a docs_count={{ ti.xcom_pull(task_ids="get_docs_count").links_count }}',
    do_xcom_push=False,
    dag=dag,
)


t4 = PythonOperator(
    task_id='process',
    python_callable= process,
    op_kwargs={"counts": "{{ti.xcom_pull('get_docs_count')}}"},
    dag=dag,
)

t5 = DummyOperator(
    task_id='topic_modeling_num_32',
    #python_callable= model,
    dag=dag,
)

t6 = DummyOperator(
    task_id='topic_modeling_num_12',
    #python_callable= model,
    dag=dag,
)

t7 = DummyOperator(
    task_id='sentiment_analysis',
    #python_callable= sentiment(),
    dag=dag,
)

t8 = DummyOperator(
    task_id='sentiment_analysis_v2',
    #python_callable= sentiment(),
    dag=dag,
)


t2.set_upstream(t1)
t3.set_upstream(t2)
t4.set_upstream(t3)

t5.set_upstream(t4)
t6.set_upstream(t4)

t7.set_upstream(t5)
t8.set_upstream(t6)