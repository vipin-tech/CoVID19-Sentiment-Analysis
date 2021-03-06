import configparser
import logging
import re
import string
import time
from datetime import datetime, timedelta
import requests
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from pymongo import MongoClient
from textblob import TextBlob
from scheduler import scheduler

# Setup the configuration file
config = configparser.ConfigParser()
config.read('tweet_tracker.cfg')

logging.basicConfig(format='%(asctime)s %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p',
                    filename='tweet_tracker.log',
                    level=logging.DEBUG)

Log = logging.getLogger('tweet_tracker.log')

# If scheduler is not running, start the scheduler
if not scheduler.running:
    scheduler.start()

headers = dict()

# Prepare the query parameters

base_url = config['DEFAULT']['BASE_URL']
query_param = config['query']['QUERY_PARAM']
headers['Host'] = config['headers']['HOST']
headers['User-Agent'] = config['headers']['USER_AGENT']
headers['Accept-Encoding'] = config['headers']['ACCEPT_ENCODING']
headers['Authorization'] = config['headers']['AUTHORIZATION']

# Establish the connection to the database
mongo_client = MongoClient(config['mongo.client']['MONGO_CLIENT'])

# Connect to the collection `recent_tweets`
recent_tweets = mongo_client.twitter_db.recent_tweets


def tag_sentiment_type(polarity):
    """ Tag the sentiment for a tweet based on the polarity. """

    sentiment_type = 'positive'

    if polarity < 0:
        sentiment_type = 'negative'

    elif polarity == 0:
        sentiment_type = 'neutral'

    return sentiment_type


def perform_sentiment_analysis(text):
    """This method perform the sentiment analysis using TextBlob which is built on nltk."""

    try:
        stop_words = set(stopwords.words('english'))

        word_tokens = word_tokenize(text)

        filtered_text = [w for w in word_tokens if not w in stop_words]
        filtered_text = " ".join(filtered_text)
        polarity, subjectivity = TextBlob(filtered_text).sentiment.polarity, TextBlob(text).sentiment.subjectivity

        sentiment_type = tag_sentiment_type(polarity)

        return polarity, subjectivity, sentiment_type

    except Exception as ex:
        Log.error(str(ex))


def clean_text(text):
    """ This method cleans up the data and returns the str """

    # googletrans is not the free api. Can make only few requests.
    # Translate the text if found in other languages.
    # if detect(text) != 'en':
    #    text = translator.translate(text).text

    text = text.lower()
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'[%s]' % re.escape(string.punctuation), '', text)
    text = re.sub(r'\n', '', text)
    text = re.sub(r'\w*\d+\w*', '', text)
    text = re.sub(r'https:\/\//s+ | http:\/\//s+', '', text)
    text = re.sub(r'rt\s+', '', text)
    text = text.replace('@', '')
    text = text.replace('#', '')
    return text


def collect_documents(result, max_id):
    insert_documents = list()
    for document in result:

        if max_id:
            if max_id >= document.get('id'):
                max_id = document.get('id')

        try:
            insert_data = dict()
            insert_data['id'] = document.get('id')
            insert_data['created_at'] = document.get('created_at')
            insert_data['name'] = document['user'].get('name')
            insert_data['screen_name'] = document['user'].get('screen_name')
            insert_data['location'] = document['user'].get('location')
            insert_data['full_text'] = clean_text(document.get('full_text'))
            insert_data['followers_count'] = document['user'].get('followers_count')
            insert_data['friends_count'] = document['user'].get('friends_count')
            insert_data['listed_count'] = document['user'].get('listed_count')
            insert_data['statuses_count'] = document['user'].get('statuses_count')
            insert_data['profile_image_url'] = document['user'].get('profile_image_url')

            # if document.get('retweeted_status'):
            #     d['retweet_status'] = document.get('retweeted_status', {})
            #     if d['retweet_status'].get('full_text'):
            #         d['retweet_status']['full_text'] = clean_text(d['retweet_status']['full_text'])

            insert_data['polarity'], insert_data['subjectivity'], insert_data['sentiment_type'] = \
                perform_sentiment_analysis(insert_data['full_text'])

            insert_documents.append(insert_data)
        except Exception as ex:
            Log.error(str(ex))
            continue

    yield insert_documents


def collect_recent_tweets():
    """
    This method collects the recent tweets for the following search tags
    - Ireland
    - Virus
    - corona virus
    """
    Log.debug("Start Collecting recent tweets.")
    # Clearing off the contents of collections when collections consists of more than 100000 documents.
    # if recent_tweets.count_documents({}) > 100000:
    #    recent_tweets.delete_many({})

    max_id = 0
    for _ in range(100):
        try:
            if max_id:
                result = requests.get(url=base_url + 'max_id=' + str(max_id + 1) + '&' + query_param,
                                      headers=headers).json()
            else:
                result = requests.get(url=base_url + query_param, headers=headers).json()

            result = result.get('statuses')

            # Insert the documents into collection `recent_tweets`
            for documents in collect_documents(result, max_id):
                recent_tweets.insert_many(documents)

        except Exception as ex:
            Log.error("Error while collecting logs. %s", str(ex))


start_date = datetime.now() + timedelta(seconds=10)


def collect_twitter_data():

    # Set the schedule interval in configuration file.
    t = config['schedule.param']['SCHEDULE_TIME']

    job = scheduler.add_job(collect_recent_tweets, start_date=start_date,
                            trigger='interval', minutes=int(t), max_instances=4, coalesce=True)

    sleep_time = datetime.timestamp(job.next_run_time) - int(time.time())
    print("Next Wakeup Call in {}. Next Run Time {} ".format(sleep_time, job.next_run_time))
    time.sleep(sleep_time)


while True:
    collect_twitter_data()

# collect_recent_tweets()

