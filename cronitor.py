#!/usr/bin/python

import ast
import praw
import time
import datetime

import argparse
import sys,traceback
from pprint import pprint

import yaml
import asteval



def fire_action(event,subreddit,variables):
    if 'post' in event:
        title = event['post']['title']
        text = event['post']['text']
        title = time.strftime(title.format(**variables))
        text = time.strftime(text.format(**variables))
        subreddit.submit(title=title,text=text)
        
        print
        print 'sending'
        print

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
    control_page_name = config['control_page']
    cron_time = config['cron_time']
    
    
    
    r = praw.Reddit(user_agent=user_agent)
    r.login(config['reddit_user'],config['reddit_pwd'])
    subreddit = r.get_subreddit(config['subreddit'])
    
    
    min_sleep_time = .01
    now = time.time()
    last_run = now - (now % cron_time)
    
    last_run -= cron_time
    next_run = last_run + cron_time
    
    assert last_run % cron_time == 0
    assert next_run % cron_time == 0
    
    event_states = {}
    
    while True:
        now = time.time()
        #next_run = now - (now % cron_time) + cron_time
        
        
        if now < next_run:
            sleep_time = max(min_sleep_time, next_run - now + min_sleep_time)
            print 'sleeping cronitor, now:',now, 'last_run:',last_run,
            print 'next_run:',next_run,
            print 'now - last_run:', (now - last_run),
            print 'next_run - now:', (next_run - now)
            print 'sleep_time:',sleep_time
            
            time.sleep(sleep_time)
            continue

        print 'running cronitor, now:',now,'now % cron_time:',now % cron_time
        
        last_run = now - (now % cron_time)
        next_run = last_run + cron_time
        
        assert last_run % cron_time == 0
        assert next_run % cron_time == 0
        assert next_run - last_run == cron_time
        
        try:
            wiki_control_page = subreddit.get_wiki_page(control_page_name)
            wiki_config_data = wiki_control_page.content_md
            
            
            wiki_config_data = \
'''
---
    condition: "{M} % 2 == 0"
    post: 
        title: Even Minute Test, {M}
        text: Test text
---'''
            
            
            events = yaml.load_all(wiki_config_data)
            
            #pprint([event for event in events])

            current_gmtime = time.gmtime()

            #print 'variables:',variables

            variables = {}
            
            strftime_format_strings = ['a','A','b','B', 'c','d','H','I',
                'j','m','M','p','S','U','w','W','x','X','y','Y','Z']
            for format_string in strftime_format_strings:
                variables[format_string] = time.strftime(
                    '%{format_string}'.format(format_string=format_string),
                    current_gmtime)
            
            aeval = asteval.Interpreter()
            
            
            for event in events:
                try:
                    if event is None:
                        continue
                    
                    event_str = str(event)
                    
                    #print
                    #print
                    #print 'event_str:',event_str
                    #print 'event_states:',event_states
                    
                    event_state0 = None
                    if event_str in event_states:
                        event_state0 = event_states[event_str]
                        assert event_state0 is not None
                    
                    #print 'event_state0:',event_state0
                    
                    condition = event['condition']
                    condition = condition.format(**variables)
                    #condition = time.strftime(condition, current_gmtime)
                    
                    aeval.symtable = variables
                    event_state1 = aeval(condition)
                    #print '({condition})   ====>   {event_state1}'.format(condition=condition,event_state1=event_state1)

                    event_states[event_str] = event_state1
                    
                    assert event_str in event_states

                    if not isinstance(event_state1,(bool)):
                        raise ValueError('Condition did not evaluate to boolean: ' + condition)
                    
                    if event_state1:
                        if event_state0 is None:
                            #print 'state has just initialized'
                            continue
                        if event_state0:
                            #print 'condition is true, but unchanged'
                            continue
                            
                        fire_action(event,subreddit,variables)
                    
                    
                    
                except Exception as e:
                    print >> sys.stderr, 'Exception during handling event:',e
                    traceback.print_exc(file=sys.stderr)
        except Exception as e:
            print >> sys.stderr, 'Exception during handling event:',e
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
