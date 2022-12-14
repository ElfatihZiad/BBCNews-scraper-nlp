# News Article Data pipeline: Scrapy, Airflow, MongoDB, NLP Analysis.

A data pipeline to extract News artciles from [BBC News](https://www.bbc.com/news), storing it to MongoDB, performing NLP analysis (Topic modeling, sentiment analysis), and orchestrating the whole process with airflow.

## Table of contents
  - [Scraping approach](#scraping-approach)
  - [Breakdown of our Scraper](#breakdown-of-our-scraper)
  - [Scheduler](#scheduler)
  - [Database](#database)
  - [Dockerization](#dockerization)
  - [Data Processing](#data-processing)
  - [Topic Modeling](#topic-modeling)
    - [some key takeawyas](#some-key-takeawyas)
  - [Sentiment Analysis](#sentiment-analysis)
  - [output data](#output-data)
  - [Next steps and improvements:](#next-steps-and-improvements)
  - [Setup](#setup)

## Scraping approach

Our approach will save us the pain to scroll through the entire Website Menus and Submenus, and navigate all the pages programmatically to get articles URLs.

By looking into [Robots.txt](https://www.bbc.com/robots.txt) we can find links to the website's sitemaps.

According to [wikipedia](https://en.wikipedia.org/wiki/Sitemaps):
> .. A Sitemap is an XML file that lists the URLs for a site. It allows webmasters to include additional information about each URL [...] This allows search engines to crawl the site more efficiently and to find URLs that may be isolated from the rest of the site's content.  

There are two sitemaps in the robots.txt that particularly interest us:

- One for Archived articles, it contains all the links to old articles that are otherwise inaccessible by normal navigation through the website.
> Sitemap: https://www.bbc.com/sitemaps/https-index-com-archive.xml

- The other includes URLs of articles published in the last 48 hours  
> Sitemap: https://www.bbc.com/sitemaps/https-index-com-news.xml

Accordingly, the approach with be the following:

using BeautifulSoup Libray for getting URLs from sitemaps as it's more handy when dealing with xml pages. Then collecting only News articles published in the last three months. 

We will build a database of urls and run the crawler every day, and use `Airflow` for scheduling crawls.

- The `archive_scraper.py` script collect all URLs of articles published in the last three month and store the data in a mongodb collection names `links` (note that the archive scraper will only have to run once)
- `daily_scraper.py` script do the same for articles published in the last 48 hours.

Once we get all links, we will implement [Scrapy framework](https://scrapy.org/) to crawl through the links and get the desired data from each article. Scrapy is capable of performing concurrent requests, Default is 16. The number could be changed in the `settings.py`.

## Breakdown of our Scraper

![scraper_structure.png](https://github.com/ElfatihZiad/bbc-news/blob/main/images/scraper_structure.png)

- The main component of our scraper is `ArticleSpider.py` inside the `spiders` folder. It's where we specified links to follow which are pulled from our URLs collection on mongodb, and what items to get from each page.

- `items.py` which is used to describe a Python class that the results will be stored in.

- In the `middleware.py` we made sure that once an article was collected our spider wont make any more requests, as to both avoid duplicated data and to optimize performance. 

- In the `pipeline.py` we exclude items that doesnt contain titles, as there are some links that refers to menus or submenus and not articles. We also specified how items would be exported. In our case items were stored in another mongodb collection `NewsSpider`. Further filters or transformation could be made by adding Classes to the `pipeline.py` and specifying the order in the settings file.

## Scheduler

Airflow as orchestrator would scale well should we add more complexity to our pipeline.
The project can evolve to include more crawlers to different websites, making significant tranformations on the collected data, training ML models... Airflow is capable of orchestrating all of that.

If you check the dags folder, you'll find a file titled `bbc_news_dag.py`. This is our [DAG](https://airflow.apache.org/docs/apache-airflow/1.10.12/concepts.html#dags) which looks like the following in the Airflow's UI.

![scraper_structure.png](https://github.com/ElfatihZiad/bbc-news/blob/main/images/dag.png)

- the fist task `get_docs_count` get number of the documents stored in the database and pass it as an `XCOM` arguments to the third task, this tremendously speed up the process by making our crawl visit only the collected urls from the second task.
If this is not configured the crawler will make requests to all the links in the url database including those already visited from previous runs.

- second task `get_urls` is responsible for parsing the sitemaps and get articles URLs.

- Third task `crawl` is were the scraping of articles occurs, data obtained is saved to a mongodb collection.

- Forth task `process` make necessary tranformations and cleaning on the raw scraped data.

- Then we branch into two seperate tasks, each one performs topic modeling with different parameters, more details on this later Then we make two seperate sentiment analysis. (not yet implemented in dag file, see notebooks folder)

## Database 

For every task performed we save the output in a mongo collection
![mongo_collections.png](https://github.com/ElfatihZiad/bbc-news/blob/main/images/mongo.png)

## Dockerization

we Created a Dockerfile pointing to Airflow version apache/airflow:2.2.3, as the base image,and adding our custom packages to be installed and integrating requirements.txt to install libraries via pip install.

For this project, the docker-compose.yaml file comes from the Airflow in Docker quick-start guide. This defines all the services we need for Airflow, e.g., scheduler, web server, and so forth.

When we run this docker-compose file, it will start our services. I've changed a few things in this file:

```
mongo:
    container_name: mongo
    image: mongo:5.0
    ports:
        - 27017:27017
    volumes:
        - ./mongo:/data/db
```
These extra lines add a mongodb service and maps the host port with the container port so we can access it from our local machine, and mount the mongo folder on our local file system to the docker containers. 

## Data Processing


From every article, we remove:

  - White spaces at the beginning and at the end of the text and HTML tags.
  - Every character that are not a digit nor an alphabetical letter
  - The punctuations
  - The english stop-words
  - The words that are not an adjective, a noun, or an adverb.

Then we use lemmatization to turn every word to its base or dictionary form.
Output data is saved in a MongoDB collection `articles_processed`

## Topic Modeling

we take the processed articles and we train multiple LDA models and compute the coherence metric for a range of topic numbers. 
Finally, we train the final LDA model with the optimal number of topics. a topics number of 32 gives a coherence score of 0.54 Which is decent.
we then trained two models: one for topics number set to 32 for more detailed sub-topics/sub-categories, and another model of 12 topics for more general topics/categories.

I then analysed topics through the relevance metric and words frequency/rarity to come up with a label for each topic.
This is my result:
```
[[0, 'lgbtq'],
[1, 'Boris Johnson'], 
[2, 'environment'], 
[3, 'Asylum'],
[4, 'Archie Battersbee'],
[5, 'northern ireland'],
[6, 'health'],
[7, 'rescue'],
[8, 'abortion'],
[9, 'allegations'],
[10, 'transportation'],
[11, 'sport'],
[12, 'weather'],
[13, 'crime'],
[14, 'afghanistan'],
[15, 'royal_family '],
[16, 'housing'],
[17, 'events'],
[18, 'energy'],
[19, 'russian-ukrain war'],
[20, 'road'],
[21, 'world'],
[22, 'fire'],
[23, 'cancer'],
[24, 'trial'],
[25, 'art'],
[26, 'school'],
[27, 'concil'],
[28, 'child'],
[29, 'airplanes'],
[30, 'taiwan'],
[31, 'economy'],                
              ]
```

The folowing image show the LDA plot where 32 topics are clustered. On the left, the clusters are shown which their size indicates the marginal topic distribution. On the right, the most important words of a topic are shown with their frequency measure within that topic (red bars) versus their overall frequency in the entire corpus (blue bars).

by looking at the ldaplot we can clearly conclude that dominant theme in this topic is asylum & immigration.
![lda_plot_topic_asylum](https://github.com/ElfatihZiad/bbc-news/blob/main/images/lda_plot_topic_asylum.png)

You could run your own analysis by checking out these files: `bbc-news-topics_32.html` and `bbc-news-topics_12.html`

Here is topics I come up with with `num_topics` paramter set to 12 for more general topics.
```
 [[0, 'local'],
  [1, 'politics'], 
  [2, 'boris johnson'], 
  [3, 'environment'],
  [4, 'crime'],
  [5, 'russia-ukraine'],
  [6, 'family'],
  [7, 'royal family'],
  [8, 'fire'],
  [9, 'economy'],
  [10, 'world'],
  [11, 'entertainmeent']]
```

### some key takeawyas

- Topics returned were biased towards local uk news as a big portion of articles on the site are local althought they dont often make the home page.
- Topics were also heavily influenced by recent events as they inlude only last three months: heatwave, price rise, russia-ukraine, recent incidents.


## Sentiment Analysis

we calculated Polarity and Subjectivity for each article, and map it for its respective topic.

The figure below shows polarity and subjectivity trend over time.
![polarity](https://github.com/ElfatihZiad/bbc-news/blob/main/images/polarity_trend.png)
![subjectivity](https://github.com/ElfatihZiad/bbc-news/blob/main/images/subjectivity_trend.png)

The figure below shows the evaluation of the polarity per topic over time.

As expected, crime, politics, and russia-ukraine topics are more negative than the other topics, as there is rarely good news when it comes to crime. We also observe a surge in negativity in the environement topic as result of recent wildfires and heatwaves.

![sentiments_12](https://github.com/ElfatihZiad/bbc-news/blob/main/images/plot_sentiments_12.png)

The figure below shows the sentiment trends of sub-topics (32 topics) and their evolution of sentiment over time.

We can extract lot of information from this plot by checking the sentiment change and its date, and looking up relevant news from that exact date. 
![sentiments_12](https://github.com/ElfatihZiad/bbc-news/blob/main/images/plot_sentiments_32.png)


## output data
In the data folder there are 4 csv files:
- `scraped_articles.csv` : contains raw data that were scraped, resulted from the `crawl` task in the airflow dag
- `articles_processed.csv` : cleaned and processed articles, resulted from the `process` task in the airflow dag.
- `articles_lda_12.csv` : articles categorized into 12 topics.
- `articles_sentiments.csv`: polarity and subjectivity score for every article.

## Next steps and improvements:
Feel free to make suggestions.
## Setup

Software required to run the project. Install:

- [Docker](https://docs.docker.com/get-docker/)
- [Python 3.8+ (pip)](https://www.python.org/)
- [docker-compose](https://docs.docker.com/compose/install/)

> **NOTE**: This was developed using Linux. If you're on Windows or Mac, you may need to amend certain components if issues are encountered.


First clone the repository into your home directory and follow the steps.

  ```bash
  git clone https://github.com/
  cd project
  ```

Then to build the project components run, This will take a few minutes. Make sure the Docker daemon (background process) is running before doing this.
   ```bash
  docker-compose build
  ```
Create our Airflow containers. This could take a while. You'll know when it's done when you get an Airflow login screen at http://localhost:8080
   ```bash
docker-compose up
  ```

If interested, once containers are created you can them from the command line with:

```bash
docker ps
```

You can connect into a docker container and navigate around the filesystem:

```bash
docker exec -it <CONTAINER ID> bash
```

As mentioned above, navigate to http://localhost:8080 to access the Airflow Web Interface. This is running within one of the Docker containers, which is mapping onto our local machine with port 8080. Password and username are both `airflow`

to shut down the airflow containers, run the following command from the airflow directory:
```bash
docker-compose down
```
