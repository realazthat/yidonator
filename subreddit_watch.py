#!/usr/bin/env python

# built-in modules
import re
import sys
import json
import time
import traceback
from pprint import pprint

# http://python-requests.org
import requests

# https://github.com/praw-dev/praw
import praw

# local modules
from tool_utils import shorten_url, unescape_entities
from reddit_tools.new_post_monitor import NewPostMonitor
from reddit_tools.new_comment_monitor import NewCommentMonitor 



import yaml
import argparse

def reddit_format_escape(unformatted_text):
    result = []
    
    special_chars = set(['*','[',']','(',')','^','\\','`'])
    for c in unformatted_text:
        if c in special_chars:
            result += ['\\', c]
        else:
            result += c
    
    return ''.join(result)
    
    


class Collector:
    def __init__(self, r, regex):
        self.r = r
        self.regex = regex
        
        self.results = []
        self.notify_users = []
        self.post_count = 0
        
    def collect_post(self,jpost):
        print >> sys.stderr, "collect_post()"
        
        regex = self.regex
        
        self.post_count += 1
    
        permalink = 'http://www.reddit.com{permalink}'.format(permalink=unescape_entities(jpost['data']['permalink']).encode('utf-8'))
        
        domain = unescape_entities(jpost['data']['domain'])
        url = unescape_entities(jpost['data']['url'])
        
        title = unescape_entities(unescape_entities(jpost['data']['title']))
        author = unescape_entities(jpost['data']['author'])
        selftext = unescape_entities(jpost['data']['selftext'])
        
        if regex.search(title.lower()) is not None or regex.search(selftext.lower()) is not None:
            #permalink = shorten_url(permalink)
            
            title = reddit_format_escape(title)
            title = title.encode('utf-8')
            permalink = permalink.encode('utf-8')
            
            self.results += ['* **{title}**\n\n \\[[link]({permalink})\\]'.format(title=title,permalink=permalink)]
            
    def collect_comment(self,jpost):
        pass
    
    def run(self):    
        print >> sys.stderr, 'processed {n} posts with {m} positive results.'.format(n=self.post_count, m=len(self.results))
        if len(self.results) != 0:
            message = '\n'.join(self.results)
            for recipient in self.notify_users:
                try:
                    self.r.send_message(recipient,subject='New relevant posts', message=message, raise_captcha_exception=True)
                except Exception as e:
                    print >> sys.stderr, 'exception while trying to notify users:',e
                    traceback.print_exc(file=sys.stdout)
        
        self.results = []
        self.post_count = 0


def main():
    
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('config', type=argparse.FileType('r'),help="configuration file")

    parsed_args = parser.parse_args()

    config_file = parsed_args.config

    config = {}

    try:
        config = yaml.load(config_file)
    except:
        print >> sys.stderr
        print >> sys.stderr, "ERROR: parsing configuration"
        print >> sys.stderr
        
        raise
    
    main_context = {}
    
    main_context['config'] = config
    
    
    
    user_agent = config['user_agent']
    loop_time = config['loop_time']
    limit_per_query = 50
    user_agent = config['user_agent']
    subreddit = config['subreddit']
    
    r = praw.Reddit(user_agent=user_agent)
    r.login(config['reddit_user'],config['reddit_pwd'])
    
    
    words = config['words']
    
    regex = re.compile('|'.join(map(lambda word: '({word})'.format(word=word),words)))
    
    
    new_comment_monitor = NewCommentMonitor(subreddit, limit_per_query, user_agent)
    new_post_monitor = NewPostMonitor(subreddit, limit_per_query, user_agent)
    collector = Collector(r,regex)
    collector.notify_users += config['notify_users']
    
    
    new_comment_monitor.cbs += [collector.collect_comment]
    new_post_monitor.cbs += [collector.collect_post]
    
    new_post_monitor.debug = True
    
    services = [
        #new_comment_monitor.run,
        new_post_monitor.run,
        collector.run,
        ]
    
    
    while True:
        
        for service in services:
            try:
                service()
            except Exception as e:
                
                print >> sys.stderr, 'Exception during service():',e
                traceback.print_exc(file=sys.stderr)            
        
        time.sleep(loop_time)

    
    
    
if __name__ == "__main__":
    main()
