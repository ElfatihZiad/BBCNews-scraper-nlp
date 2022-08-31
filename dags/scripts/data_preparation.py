from pymongo import MongoClient

import re
import nltk
import pandas as pd
import string

nltk.download('stopwords')
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')


def load_data(counts):
    N = int(counts['articles_count'])
    client = MongoClient('mongo',27017) # Make sure mongodb server is running
    db = client.bbcnews
    articles = db.NewsSpider
    df = pd.DataFrame(list(articles.find().sort('date',-1).limit(1000))) # N
    return df

def export_data(df):
    client = MongoClient('mongo',27017) # Make sure mongodb server is running
    db = client.bbcnews
    db['articles_processed'].insert_many(df.to_dict('records'))


def clean(text):
    
    if not isinstance(text, str):
        raise TypeError("Argument 'text' must be a string.")
    
    # Strip the text, lowercase it, and remove the HTML tags and punctuations
    text = text.lower().strip()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[^ 0-9a-z]', ' ', text)
    text = re.sub(r'\b(\d+\d)\b', '', text)
    text = re.sub(r'http|https|www', '', text)
    text = re.sub(r'\b[a-z]\b', '', text)
    text = re.sub(r' +', ' ', text)
    text = text.translate(text.maketrans('', '', string.punctuation)) #extra punctuations removal

    # Remove all the stop words
    stop_words = nltk.corpus.stopwords.words('english')
    stop_words.extend([
        'from', 're', 'also'
    ])
    stop_words = {key: True for key in set(stop_words)}
    
    # Keep only specific pos (part of speech: nouns, adjectives, and adverbs)
    keep_pos = {key: True for key in ['NN','NNS','NNP','NNPS', 'JJ', 'JJR', 'JJS','RB','RBR','RBS']}
    
    return " ".join([word 
                     for word, pos in nltk.tag.pos_tag(text.split()) 
                     if len(word) > 2 and word not in stop_words and pos in keep_pos])



def lemmatize(text: str, lemmatizer: nltk.stem.WordNetLemmatizer) -> str:

    if not isinstance(text, str):
        raise TypeError("Argument 'text' must be a string.")

    lemmas = []
    tag_dict = {
        "J": nltk.corpus.wordnet.ADJ,
        "N": nltk.corpus.wordnet.NOUN,
        "V": nltk.corpus.wordnet.VERB,
        "R": nltk.corpus.wordnet.ADV
    }
    
    tokenized_words = nltk.word_tokenize(text)
    for tokenized_word in tokenized_words:
        tag = nltk.tag.pos_tag([tokenized_word])[0][1][0].upper() # Map POS tag to first character lemmatize() accepts
        wordnet_pos = tag_dict.get(tag, nltk.corpus.wordnet.NOUN)
        lemma = lemmatizer.lemmatize(tokenized_word, wordnet_pos)
        lemmas.append(lemma)
    
    return " ".join(lemmas)

def process(**kwarg):

    counts = kwarg['counts']
    articles = load_data(counts)
    print(articles.head())

    articles = articles.dropna()
    articles["n_words"] = articles["text"].apply(lambda text: len(text.split(" ")))
    articles = articles[articles["n_words"] >  50]
    articles["article_clean"] = articles["text"].apply(clean)
    lemmatizer = nltk.stem.WordNetLemmatizer()
    articles["article_clean"] = articles["article_clean"].apply(lambda x: lemmatize(x, lemmatizer)) 
    articles["n_words_clean"] = articles["article_clean"].apply(lambda x: len(x.split(" ")))
    articles.drop(columns=['images', 'topic_name', 'topic_url', 'link', 'authors', '_id'], inplace=True)
    articles['date'] = pd.to_datetime(articles['date'])
    articles.reset_index(level=0, inplace=True)
    articles.drop(columns=['index'], inplace=True)

    print('Finished processing ...')
    print(articles.head())

    export_data(articles)