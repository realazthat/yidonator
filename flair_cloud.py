#! /usr/bin/env python

import requests

def fetch_page_of_flair(subreddit, after=None, limit=500):
    parameters = {'limit': limit}
    if after != None: parameters['after']=after

    url = "http://reddit.com/r/{subreddit}/api/flairlist.json".format(subreddit = subreddit)

    data = requests.get(url, params = parameters)
    return data.json() # a dictionary ('previous', 'users', 'next')

def collect_flair_from_api_page(api_page):
    flair_list = []
    for user in api_page['users']:
        flair = user['flair_text']
        if flair != None:
            flair_list.append(flair)
        else:
            flair_list.append('')
    return flair_list

def flair_counts(list_of_flair):
    flair_count_dictionary = {}

    for flair in list_of_flair:
        if flair in flair_count_dictionary:
            flair_count = flair_count_dictionary[flair]
        else:
            flair_count = 0

        flair_count_dictionary[flair] = flair_count + 1

    return flair_count_dictionary

def add_flair_dictionaries(dictionary_1, dictionary_2):
    for key in dictionary_2:
        if key in dictionary_1:
            dictionary_1[key] += dictionary_2[key]
        else:
            dictionary_1[key] = dictionary_2[key]

def full_subreddit_flair_count(subreddit):
    flair_count_dictionary = {}

    page_of_flair = fetch_page_of_flair(subreddit)

    while 'next' in page_of_flair:
        flair_list = collect_flair_from_api_page(page_of_flair)

        new_flair_dictionary = flair_counts(flair_list)
        add_flair_dictionaries(flair_count_dictionary, new_flair_dictionary)

        page_of_flair = fetch_page_of_flair(subreddit, after=page_of_flair['next'])

    return flair_count_dictionary


if __name__ == "__main__":
    from sys import argv as arguments
    if len(arguments) < 2:
        print "Too few arguments; requires subreddit"
    else:
        from pprint import pprint
        pprint(full_subreddit_flair_count(arguments[1]))

