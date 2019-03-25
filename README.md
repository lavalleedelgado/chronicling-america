# Chronicling America
Text search and basic sentiment analysis of historic newspaper articles from the Chronicling America project at the United States Library of Congress.
* **news_sentiment.py** requests newspaper articles containing any of the given keyword parameters within the specified year range, inclusive, and runs a TextBlob sentiment analysis on the subset of sentences in an article that include keywords.
* **plot_news_sentiment.py** offers two graphical interpretations of the data in contrast with some other data expressed annually: (1) frequency of keyword mentions annually and (2) proportion of negative sentiment in keyword mentions annually.

## Getting started
Clone or download this repository. Chronicling America requires Bokeh, Pandas, TextBlob, and dependencies:

```
$ pip install bokeh
$ pip install pandas
$ pip install textblob
```

**Note:** the [Chronicling America API](https://chroniclingamerica.loc.gov/about/api/) on which **news_sentiment.py** relies is very slow. The example that follows shows the API fulfilled one query for 5000 articles in 53 minutes. I recommend you test your implementation with a smaller query within a narrower year range.

## Sample implementation
The inspiration for Chronicling America arose from a curiosity of whether and how the conversation around immigration to the United States followed the real manifestation of immigration to the United States.

### news_sentiment.py
At the command line, the program expects at least four arguments:
* space-delimited keyword parameters
* inclusive lower bound year
* inclusive upper bound year
* year increment
* maximum number of news articles per query

```
$ python news_sentiment.py immigrant immigration migrant migration 1820 1960 5 5000
```

The year increment argument defines the interval by which to segment into discrete queries the range given by the lower and upper bound arguments. News articles within the date scope of each query must mention at least one of the keywords given. The maximum number argument limits the size of each query.

This example for news articles containing any of "immigrant", "immigration", "migrant", "migration" between the years 1820 and 1960 inclusive results in 29 discrete queries of up to 5000 news articles each, i.e. 1820-1824, 1825-1829, …, 1955-1959, 1960-1960.

Each query returns a CSV file of results, in which each row represents one article described by nine fields:
* article date
* publication state
* publication county
* publication city
* publication title
* article text
* sentences from article text with keywords
* polarity score of selected sentences [-1.0, 1.0]
* subjectivity score of selected sentences [0.0, 1.0]

The sentiment analysis only considers the sentences from the article text that include any of the keywords in an effort to isolate the context in which they appear. TextBlob analyzes those sentences of each article as one unit of text. The sign of the polarity score indicates whether the sentiment of the context in which keywords appear is negative or positive. The absolute distance from zero of the polarity and subjectivity scores express the strength of those indicators.

The program also returns a CSV file of the log, in which each row represents one query described by seven fields:
* path to query results
* keyword arguments
* inclusive lower bound year
* inclusive upper bound year
* number of results collected
* number of results available
* length of time to fulfill in seconds

The log allows plot_news_sentiment.py to locate the results and calculate weights for each interval in the total range of years.

**Note:** the Chronicling America API sometimes times out and the request results in a server error. news_sentiment.py attempts to handle this by pausing for one minute and then trying the request again. Requests raises an exception when this does not work. Run the program again with an updated inclusive lower bound year argument that reflects progress so far. You may notice the task time for the next query decrease because some of the results exist in cache.

The CSV files and log may or may not be useful for your implementation. Instead, import news_sentiment.py for the ChroniclingAmerica object:

```
import news_sentiment as ns

keywords = ["immigrant", "immigration", "migrant", "migration"]
year_min = 1820
year_max = 1960
results_max = 5000
immigration = ns.ChroniclingAmerica(keywords, year_min, year_max, results_max)

immigration.news # results as Pandas DataFrame
immigration.request_time # seconds to fulfill request as float
immigration.request_size # records collected, records available as tuple
```

### plot_news_sentiment.py
At the command line, the program expects at least four arguments:
* path to log CSV from news_sentiment.py
* path to comparison data CSV
* comparison data name

**Note:** the comparison data CSV must have "year" and "count" columns.

```
$ python plot_news_sentiment.py "immigrant-log.csv" "annual-immigration-1820-1960.csv" US Immigration
```

The program reads the log to locate and merge the results from news_sentiment.py, assigns weights to each year, and assigns appropriate axes. The weights correct the volume of news articles in a year by the ratio of news articles collected and available from the Chronicling America API for the query of corresponding date scope.

This example contrasts (1) the sentiment analysis of news articles containing any of "immigrant", "immigration", "migrant", "migration" between the years 1820 and 1960 inclusive with (2) data of annual immigration to the US. The log reports that news_sentiment.py collected only 5000 of 7952 articles for the query with date scope from 1850 through 1854; the program assigns a weight of 7952 / 5000 = 1.5904 to the volume of news articles observed for the years 1850, 1851, 1852, 1853, and 1854.

The Bokeh plots as HTML files may or may not be interesting or comprehensive for your implementation. Instead, import plot_news_sentiment.py for the functions that collect and manipulate the Chronicling America data for these plots:

```
from plot_news_sentiment import prepare_news_sentiment, prepare_news_volume, calculate_axis_range

log = pd.read_csv("immigrant-log.csv")
immigration_sentiment = prepare_news_sentiment(log)
immigration_weighted_volume = prepare_news_volume(log, immigration_sentiment)
y_min, y_max = calculate_axis_range(immigration_weighted_volume["w_volume"])
```

## Assumptions for analysis
The usefulness of Chronicling America as a representative sample rests on several major assumptions:
* the news articles collected are a random sample of the news articles available
* the news articles available are a random sample of the news articles published
* an accurate optical character recognition tool rendered the article text
* the interpretation of the English language is consistent across years
