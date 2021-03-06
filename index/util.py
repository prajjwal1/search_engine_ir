# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from nltk.corpus import stopwords
import nltk
from nltk import WordNetLemmatizer
import numpy as np
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import tldextract
import time
lemmatizer = WordNetLemmatizer()
session = requests.Session()


def preprocess(text):
    """"
    Preprocess text to generate tokens by tokenizing and lemmatizing the text using WordNet
    """
    tokens = nltk.word_tokenize(text)
    return [lemmatizer.lemmatize(token.lower()) for token in tokens if token]


def read_json(dir):
    """
    Read json to get tokens and the page links
    """
    # contains tokens for all docs
    page_tokens = {}
    # map page -> other page
    outgoing_edges = {}
    # map other page -> page
    ingoing_edges = {}
    page_ids = {}

    page_index = 0
    with open(dir, 'r') as file:
        pages = json.loads(file.read())
    for page in pages:
        text = page['text']
        source_page = page['url_from']
        # target page has the text
        target_page = page['url_to']

        if source_page not in page_ids:
            page_ids[source_page] = page_index
            page_index += 1

        if target_page not in page_ids:
            page_ids[target_page] = page_index
            page_index += 1

        if target_page not in page_tokens:
            tokens = preprocess(text)
            page_tokens[target_page] = tokens

        if source_page not in outgoing_edges:
            outgoing_edges[source_page] = []
        outgoing_edges[source_page].append(target_page)

        if target_page not in ingoing_edges:
            ingoing_edges[target_page] = []
        ingoing_edges[target_page].append(source_page)

    with open('page_tokens.json', 'w') as file:
        file.write(json.dumps(page_tokens))
    with open('ingoing_edges.json', 'w') as file:
        file.write(json.dumps(ingoing_edges))
    with open('outgoing_edges.json', 'w') as file:
        file.write(json.dumps(outgoing_edges))
    with open('page_ids', 'w') as file:
        file.write(json.dumps(page_ids))

    return page_tokens, ingoing_edges, outgoing_edges, page_ids


def load_processed_tokens():
    with open('page_tokens.json', 'r') as file:
        page_tokens = json.loads(file.read())
    with open('ingoing_edges.json', 'r') as file:
        ingoing_edges = json.loads(file.read())
    with open('outgoing_edges.json', 'r') as file:
        outgoing_edges = json.loads(file.read())
    with open('page_ids', 'r') as file:
        page_ids = json.loads(file.read())

    return page_tokens, ingoing_edges, outgoing_edges, page_ids


def load_data_for_elastic_search(dir):
    with open(dir, 'r') as file:
        pages = json.loads(file.read())
    pages_text = {}
    for page in pages:
        page_name = page['url_to']
        text = page['text']
        pages_text[page_name] = text
    master_output = []
    _, ingoing_edges, outgoing_edges, _ = load_processed_tokens()
    num = 0
    for page_name in pages_text:
        page_text = pages_text[page_name]
        if page_name in ingoing_edges:
            ingoing_edge = ingoing_edges[page_name]
        else:
            ingoing_edge = []
        if page_name in outgoing_edges:
            num += 1
            outgoing_edge = outgoing_edges[page_name]
        else:
            outgoing_edge = []
        master_output.append({'page_name': page_name, 'ingoing_edges': ingoing_edge, 'outgoing_edges': outgoing_edge,
                              'page_text': page_text})
    print(num)
    with open('elastic_search_data.json', 'w') as file:
        file.write(json.dumps(master_output))


def load_stop_words():
    return set(stopwords.words('english'))


def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def get_titles_and_description():
    with open('../crawl/travel.json', 'r') as file:
        pages = json.loads(file.read())
    processes = []
    with open('pages_info.json', 'w') as file:
        with ThreadPoolExecutor(max_workers=10) as executor:
            for page in pages:
                url = page['url_to']
                processes.append(executor.submit(multithread_process, url))
            count = 0
            for task in as_completed(processes):
                print('Finished Processing Doc {}'.format(count))
                count += 1
                try:
                    html_doc, page_link = task.result()
                    soup = BeautifulSoup(html_doc, 'lxml')
                    desc = soup.find("meta", property="og:description")
                    title = soup.find("meta", property="og:title")
                    if desc is None:
                        desc = "No description available"
                    else:
                        desc = desc['content']
                    if title is None:
                        title = "No title available"
                    else:
                        title = title['content']
                    if len(desc) > 150:
                        desc = desc[0:150]
                    file.write(json.dumps({'title': title, 'desc': desc}))
                except Exception as exc:
                    print('%r generated an exception: %s' % (url, exc))





def multithread_process(page):
    html_doc = session.get(page).text
    return html_doc, page


def parse_page_html(page_link):
    html_doc = session.get(page_link).text
    soup = BeautifulSoup(html_doc, 'lxml')
    desc = soup.find("meta", property="og:description")
    title = soup.find("meta", property="og:title")
    if desc is None:
        desc = "No description available"
    else:
        desc = desc['content']
    if title is None:
        title = "No title available"
    else:
        title = title['content']
    if len(desc) > 150:
        desc = desc[0:150]
    return title, desc


def get_page_text(dir):
    """
    Read json to get tokens and the page links
    """
    # contains tokens for all docs
    pages_text = {}

    with open(dir, 'r') as file:
        pages = json.loads(file.read())
    for page in pages:
        page_name = page['url_to']
        text = page['text']
        pages_text[page_name] = text
    print(len(pages))
    with open('pages_text.json', 'w') as file:
        file.write(json.dumps(pages_text))

def get_result(sites):
    processes = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for url in sites:
            processes.append(executor.submit(multithread_process, url))
        count = 0
        data = {}
        for task in as_completed(processes):
            count += 1
            try:
                html_doc, page_link = task.result()
                soup = BeautifulSoup(html_doc, 'lxml')
                desc = soup.find("meta", property="og:description")
                title = soup.find("meta", property="og:title")
                if desc is None:
                    paragraph = soup.find("p")
                    if paragraph is None:
                        desc = "No description available"
                    else:
                        desc = paragraph.text[0:150]
                else:
                    desc = desc['content']
                if title is None:
                    # do some heuristics to extract title
                    try:
                        title = tldextract.extract(page_link).domain.capitalize()
                    except:
                        title = "No title available"
                else:
                    title = title['content']
                if len(desc) > 150:
                    desc = desc[0:150]
                data[page_link] = {'url': page_link, 'title':title, 'desc': desc}
            except Exception as exc:
                print('%r generated an exception: %s' % (url, exc))
                return [{'url': url, 'title':"No Title Available", 'desc':'No Description Available'} for url in sites]
    docs = []
    # maintain the sorted order
    for site in sites:
        docs.append(data[site])
    return docs

if __name__ == '__main__':
    # load_data_for_elastic_search('../crawl/travel.json')
    # get_titles_and_description()
    start = time.time()
    print(get_result(['https://www.thrillophilia.com/cities/geneva', 'http://www.google.com']))
    end = time.time()
    print(end-start)
    # get_page_text('../crawl/travel.json')
