#! /usr/bin/env python

import requests

def collect_flairs(subreddit, after=None):
    """ Collects all the flairs in a subreddit,
        and returns a list of flair that are used in that subreddit."""

    flair_list = []
    url = 'http://reddit.com/r/{sr}/api/flairlist.json'.format(sr=subreddit)
    p = {'limit':1000} # 1000 is the maximum limit allowed by reddit's api
    if after != None: p['after'] = after
    data = requests.get(url, params=p).json()

    for user in data['users']:
        flair_list.append(user['flair_text'])

    # recursively collect the next batch of flairs, if there are any more
    if 'next' in data:
        flair_list += collect_flairs(subreddit, after=data['next'])

    return flair_list

def flair_counts(list_of_flair):
    """ Takes a list of flair, and return a dictionary of unique flairs mapped
        to the number of times each flair appears in the list."""

    flair_count_dictionary = {}

    for flair in list_of_flair:
        if flair in flair_count_dictionary:
            flair_count = flair_count_dictionary[flair]
        else:
            flair_count = 0
        
        flair_count_dictionary[flair] = flair_count + 1
    
    return flair_count_dictionary

def flair_count_for_subreddit(subreddit):
    """ Takes a subreddit, and returns a dictionary of the flairs
        used in that subreddit and how many times each one is used."""

    flair_list = collect_flairs(subreddit)
    return flair_counts(flair_list)

if __name__ == "__main__":
    from sys import argv as arguments
    if len(arguments) < 2:
        print "Too few arguments; requires subreddit"
    else:
        from pprint import pprint
        subreddit = arguments[1]
        """ For testing purposes, the flair_count dictionary is 
            calculated in stages, so that the numbers can be displayed."""

        flairs = collect_flairs(subreddit)
        counts = flair_counts(flairs)
        pprint(counts)
        print
        print "Users with flair:", len(flairs)
        print "Unique flairs:", len(counts)