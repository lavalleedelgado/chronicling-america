'''
News Sentiment from Chronicling America
Patrick Lavallee Delgado
University of Chicago, Harris MSCAPP '20
March 23, 2019

'''

import os
import re
import requests
import sys
import time
import pandas as pd
from textblob import TextBlob


class ChroniclingAmerica():

    '''
    Representation news articles from the Chronicling America repository at the
    Library of Congress per keyword and date parameters.

    '''

    URL = "https://chroniclingamerica.loc.gov/search/pages/results/?"

    def __init__(self, keywords, year_min, year_max, results_max):

        '''
        Initialize a ChroniclingAmerica object and immediately request and
        analyze news per parameters.

        keywords (str or lst): words of interest, any of which may appear.
        year_min (int): earliest year from which to consider news (inclusive).
        year_max (int): latest year from which to consider news (inclusive).
        results_max (int): maximum number of results allowed per query.

        NB: results_max is a soft boundary. The object does not request the
        next page if the number of results meets or exceeds results_max while
        collecting the current page.

        '''

        if isinstance(keywords, str):
            keywords = re.split(r"[\W\s]+", keywords)
        self.parameters = (keywords, year_min, year_max)
        assert self._valid_parameters(self.parameters)
        self.request_time = 0.0
        self.request_size = 0
        self.news = self._request_and_analyze(results_max, keywords)
    

    def _valid_parameters(self, parameters):

        '''
        Verify that keyword and year parameters are of appropriate types.

        parameters (tupl): keyword and year constraints for query.

        Return truth value (bool).

        '''

        keywords, year_min, year_max = parameters
        if not all(isinstance(keyword, str) for keyword in keywords):
            raise TypeError("Keywords must be of type string.")
        if not isinstance(year_min, int) and not isinstance(year_max, int):
            raise TypeError("Years must be of type integer.")
        return True
        
    
    def _request_and_analyze(self, results_max, keywords):

        '''
        Request and analyze news from the Chronlicling America API per keyword
        and data parameters.

        keywords (lst): words of interest, any of which may appear.
        results_max (int): maximum number of results allowed per query.

        Return news (DataFrame)

        '''

        news = self._build_dataset(results_max)
        news = self._build_sentiment(news, keywords)
        return news


    def _build_dataset(self, results_max):
        
        '''
        Build a dataset of the Chronlicling America API query results.

        results_max (int): maximum number of results allowed per query.

        Return data (DataFrame).

        '''

        COLUMNS = ["date", "state", "county", "city", "title", "ocr_eng"]
        raw_data = self._request_data(results_max)
        raw_data = pd.DataFrame.from_dict(raw_data, orient="columns")
        raw_data = raw_data[COLUMNS]
        raw_data["date"] = pd.to_datetime(raw_data["date"])
        return raw_data


    def _request_data(self, results_max, rows=20, page=1):

        '''
        Request the Chronlicling America API until query fulfillment. Specially
        prepare the request to avoid re-encoding plus "+" characters in the
        keyword parameter.

        results_max (int): maximum number of results allowed per query.
        rows (int): number of results to return with each request.
        page (int): page from which to collect query results.

        Return JSON (dict).

        '''

        URL = ChroniclingAmerica.URL
        json = []
        with requests.Session() as session:
            while session:
                request = requests.Request(method="GET", url=URL)
                prepped = request.prepare()
                prepped.url = URL + self._build_query(rows, page)
                request = session.send(prepped)
                if request.status_code != requests.codes.ok:
                    request = self._request_again(session, prepped)
                results = request.json()
                json.extend(results["items"])
                self.request_time += request.elapsed.total_seconds()
                self.request_size = (results["endIndex"],results["totalItems"])
                if self._fulfilled_query(results, results_max):
                    break
                page += 1
        return json


    def _request_again(self, session, prepped):

        '''
        Wait 60 seconds and retry the request. This handles the common case
        where the Chronicling America API responds with a server error.

        session (Session): current session through which to pass request.
        prepped (PreparedRequest): request with query parameters.

        Return executed request (Response) or raise RuntimeError.

        '''

        try:
            time.sleep(60)
            request = session.send(prepped)
            request.raise_for_status()
        except:
            raise RuntimeError("HTTP " + str(request.status_code) + \
            " error after pause and second attempt. Try again later.")
        return request


    def _fulfilled_query(self, results, results_max):

        '''
        Determine whether to request the next page of query results, conditions
        for which require that the request is not on the last page of results
        and that the number of results has not yet exceeded the maximum number
        of results allowed.

        results (dict): JSON from executed request.
        results_max (int): maximum number of results allowed per query.

        Return truth value (bool).

        '''

        last_page = results["endIndex"] == results["totalItems"]
        above_max = results["endIndex"] >= results_max
        return last_page or above_max


    def _build_query(self, rows, page):

        '''
        Build a query for the Chronicling America API with which to parametize
        the request object. Delimit keywords with the plus "+" character.

        rows (int): number of query results to return with one request.
        page (int): counter of number of requests towards fulfilling one query.

        Return query (str).

        '''

        keywords, year_min, year_max = self.parameters
        query = {"ortext": "+".join(keywords),
                 "dateFilterType": "yearRange",
                 "date1": year_min,
                 "date2": year_max,
                 "format": "json",
                 "rows": rows,
                 "page": page}
        return "&".join(str(p) + "=" + str(v) for p, v in query.items())


    def _build_sentiment(self, news, keywords):

        '''
        Build a TextBlob sentiment analysis of the dataset using the sentences
        from news articles that include any of the keywords in the query.

        news (DataFrame): request results from Chronicling America API.
        keywords (lst): words of interest, any of which may appear.

        Return data (DataFrame)

        '''

        keyword_sentence_pattern = re.compile(r"(?<=\.)+[^\.]*(?:\b" + 
            r"\b|\b".join(keywords) + r"\b).*?\.", flags=re.I | re.S)
        news["key_sentences"] = news.apply(
            lambda df: re.findall(keyword_sentence_pattern,
            str(df["ocr_eng"])), axis=1)
        news["sentiment"] = news.apply(
            lambda df: TextBlob(r"\n".join(df["key_sentences"])).sentiment,
            axis=1)
        news[["polarity", "subjectivity"]] = news["sentiment"].apply(pd.Series)
        news = news.drop(columns="sentiment")
        return news
    

    def __len__(self):

        return self.news.shape[0]


def run():
    
    '''
    Collect arguments from standard input with which to create and export
    ChroniclingAmerica objects as CSV files into the present directory.

    '''

    arguments = sys.argv[1:]
    if len(arguments) < 5:
        print("Expected at least five arguments: space delimited keywords,\n"
              "inclusive upper bound year, inclusive lower bound year,\n"
              "year increment, and maximum number of records per file.")
        sys.exit()
    try:
        max_results = float(arguments.pop())
    except TypeError:
        print("Expected integer or float for the fifth argument: maximum "
              "number of records per file.")
        sys.exit()
    try:
        year_incr = int(arguments.pop())
    except TypeError:
        print("Expected integer for the fourth argument: year increment.")
        sys.exit()
    try:
        year_max = int(arguments.pop())
    except TypeError:
        print("Expected integer for the third argument: inclusive upper bound"
              " year.")
        sys.exit()
    try:
        year_min = int(arguments.pop())
    except TypeError:
        print("Expected integer for the second argument: inclusive lower bound"
              " year.")
        sys.exit()
    keywords = arguments
    num_exports = (year_max - year_min) // year_incr + 1
    for export in range(1, num_exports + 1):
        temp_min = year_min + year_incr * (export - 1)
        temp_max = min(temp_min + year_incr - 1, year_max)
        csv_path = "-".join([keywords[0], str(temp_min), str(temp_max)])+".csv"
        csv_data = ChroniclingAmerica(keywords, temp_min, temp_max,max_results)
        csv_data.news.to_csv(csv_path, index=False, escapechar="\\")
        print(_log_progress(csv_path, keywords, temp_min, temp_max, \
            csv_data.request_size, csv_data.request_time, export, num_exports))
    print("Finished!")
    sys.exit()


def _log_progress(path, keywords, year_min, year_max, size, time, export, \
    num_exports):

    '''
    Log progress with last CSV file export and update the user.

    '''

    log_path = keywords[0] + "-log.csv"
    log_data = pd.DataFrame(
        {"path": [path],
         "keywords": [keywords],
         "year_min": [year_min],
         "year_max": [year_max],
         "n_collected": [size[0]],
         "n_available": [size[1]],
         "task_time_s": [time]})
    write_or_append = "w"
    if os.path.exists(log_path):
        write_or_append = "a"
    with open(log_path, write_or_append) as log:
        if write_or_append == "w":
            log.write(log_data.to_csv(header=True, index=False))
        else:
            log.write("\n")
            log.write(log_data.to_csv(header=False, index=False))
    message = ("Collected news and analyzed sentiment from " + str(year_min) +
               " through " + str(year_max) + " in file " + str(export) + " of "
               + str(num_exports) + ".\nChronicling America fulfilled this"
               " request for " + str(size[0]) + " of " + str(size[1]) +
               " available records in " + str(round(time, 2)) + " seconds.\n")
    return message


if __name__ == "__main__":
    run()

