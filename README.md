# CoVID19-Sentiment-Analysis
![alt img](https://github.com/vipin-tech/CoVID19-Sentiment-Analysis/blob/master/_images/twitter.png) 

**Almost Realtime Sentiment Analysis on CoVID19 Twitter Data using Twitter API and Pymongo**

The main aim of this project to understand the people's reaction to CoVID.

Recent tweets is collected from Twitter using `Twitter API` related to CoVID Pandemic with the following filters.

* lang=en
* #coronavirus
* #virus
* #CoronavirusPandemic
* Ireland

Data is cleaned using python `regex`. Sentiment analysis is performed on this collected data using `Text Blob` which is built 
top of `nltk`.

The collected data is stored in MongoDB `Atlas` which provides the solution of database as a service. 

This project provides the flexibility of carrying out analysis on other topics by just altering config file `tweet_tracker.cfg`.

About 10,000 recent tweets are collected every 30 minutes. Frequency of data collection can be changed by altering the config file.

Scheduler is implemented using python library `apscheduler`.

Features CompingUp!

* Visually represent the collected data using python dash.
* Write the `systemd` service file so that this project can be deployed on any Linux operating system that has `systemd` as service manager.
