#!/usr/bin/python

import ast
import praw
import time
import datetime

import argparse
import sys,traceback
from pprint import pprint
import textwrap


import yaml
import asteval


from tool_utils import unescape_entities


class CronitorRuleException(Exception):
    pass

def fire_action(event,subreddit,variables):
    if 'post' in event:
        post = event['post']
        
        title = post['title']
        
        
        
        text = post['text'] if 'text' in post else None
        url = post['url'] if 'url' in post else None
        sticky = post['sticky'] if 'sticky' in post else False
        
        
        text = unescape_entities(text).format(**variables) if text is not None else None
        url = unescape_entities(url).format(**variables) if url is not None else None
        title = unescape_entities(title).format(**variables)
        
        if text is not None and url is not None:
            raise CronitorRuleException("cannot specify both a 'text' field and 'url' field for post action")
        
        if url is None and text is None:
            text = ' '
        if text is not None and len(text) == 0:
            text = ' '
        
        print 'title:',title,'text:',text
        
        if sticky:
            
            subreddit.submit(title=title,text=text,url=url).distinguish().sticky()
        else:
            subreddit.submit(title=title,text=text,url=url).distinguish()
        
        
        print
        print 'sending'
        print

def replytopms(config,r,subreddit):
    
    
    for message in r.get_unread():
        try:
            #pprint(vars(message))
            subject = message.subject
            
            if subject is None:
                continue
        
            tokens = subject.split(':')
            
            if len(tokens) == 0:
                continue
            
            if tokens[0] != 'cronitor':
                continue
            
            if tokens[1] == 'status' and tokens[2] == config['subreddit']:
                message.reply(subject + ':' + 'running')
                message.mark_as_read()
        
        except Exception as e:
            print >> sys.stderr, 'Exception during handling message:',e
            traceback.print_exc(file=sys.stderr)







def generate_help_string():
    help_string_lines = [
        'Condition is a python-ish expression. You can use {VARIABLE} to test against preset values.',
        'The condition MUST evaluate to True or False.',
        'Variables that are available are python\'s time formatting options.',
        'http://docs.python.org/2/library/time.html#time.strftime for time formatting options.',
        'So, for the minutes of the current hour, one could use {M}.',
        'Condition should match a range of time. The bot will fire the action when the condition changes state,\
          ie. it does not match on one run, and then it does match on the next run.',
        'If the condition matches for a short time, ie. it is shorter than the cron-time of the bot, it can be missed,\
          and other Bad Things can occur.',
        'Variables can be used in the title and text fields as well.',
        'Errors will fail silently, emitting an error in the bot logs.',
        'To see if the bot is running, you can PM the account with subject "cronitor:status:<subreddit>".'
        ]


    
    result = []
    for help_string_line in help_string_lines:
        help_string_line = ' '.join(help_string_line.split('\n'))
        help_string_line = ' '.join(help_string_line.split())
        help_string_line = textwrap.wrap(help_string_line,70)
        result += ['\n  '.join(help_string_line)]
    
    return '\n'.join(result)
        

def clear_error_lines(event_str, error_prefix):
    
    event_str_lines = event_str.split('\n')
    
    result = []
    
    for event_str_line in event_str_lines:
        if event_str_line.startswith(error_prefix):
            continue
        result += [event_str_line]
        
    return '\n'.join(result)

def update_help_header(new_event_strs,update_control_page):
    
    help_comment_prefix = '> **Cronitor Help**  ... Do not edit, this is YAML section is autogenerated\n\n'
    help_comment = help_comment_prefix \
                      + '\n'.join([ '  * ' + line if len(line) > 0 and line[0] != ' ' else '    ' + line
                                      for line in generate_help_string().split('\n')])
    if len(new_event_strs) == 0:
        new_event_strs += [help_comment]
        update_control_page = True
    else:
        if new_event_strs[0].startswith(help_comment_prefix):
            if new_event_strs[0] != help_comment:
                new_event_strs[0] = help_comment
                update_control_page = True
        else:
            new_event_strs = [help_comment] + new_event_strs
            update_control_page = True
    return new_event_strs,update_control_page
def main():
    
    #print '\n'.join([ '  * ' + line if len(line) > 0 and line[0] != ' ' else '    ' + line
    #                  for line in generate_help_string().split('\n')])
    #exit()
    
    parser = argparse.ArgumentParser(add_help=True)
    
    
    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument('--rules-usage', action='store_true')
    group.add_argument('config', type=argparse.FileType('r'),help="configuration file",nargs='?')

    parsed_args = parser.parse_args()


    if parsed_args.rules_usage:
        print '\n'.join([ '  * ' + line if len(line) > 0 and line[0] != ' ' else '    ' + line
                           for line in generate_help_string().split('\n')])
        exit()

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
            
            replytopms(config,r,subreddit)
            
            wiki_config_data = '''
---
    condition: "{M} % 2 == 0"
    post: 
        title: Even Minute Test, {M}
        text: Test text
---'''
            
            wiki_control_page = subreddit.get_wiki_page(control_page_name)
            wiki_config_data = unescape_entities(wiki_control_page.content_md)
            
            #events = yaml.load_all(wiki_config_data)
            
            event_strs = wiki_config_data.split('\n---')
            
            event_strs = [ event_str + '\n' for event_str in event_strs ] #if len(event_strs.strip()) != 0
            
            #sometimes we should update control page with parsing errors, runtime errors,
            # or with a help comment on the top
            update_control_page = False
            error_prefix = '    #--CronitorError: '
            new_event_strs = list(event_strs)
            new_event_strs = [clear_error_lines(new_event_str,error_prefix) for new_event_str in new_event_strs]
            
            
            #pprint(event_strs)
            
            events = [None] * len(event_strs)
            for i,event_str in enumerate(event_strs):
                try:
                    event = yaml.load(event_str)
                    
                    events[i] = event
                except yaml.YAMLError, exc:
                    print "Error in configuration file:", exc
                    if hasattr(exc, 'problem_mark'):
                        mark = exc.problem_mark
                        cronitor_error_str = '{error_prefix}line {line}:{column}'.format(error_prefix=error_prefix,line=mark.line+1,column=mark.column+1)
                        
                        if cronitor_error_str not in event_str.split('\n'):
                          update_control_page = True
                          new_event_strs[i] = '{event_str}\n\n{cronitor_error_str}\n'.format(event_str=event_str,cronitor_error_str=cronitor_error_str)
            #pprint(events)
                
                    
            
            
            #pprint([event for event in events])

            current_gmtime = time.gmtime()

            #print 'variables:',variables

            variables = {}
            
            strftime_format_strings = ['a','A','b','B', 'c','d','H','I',
                'j','m','M','p','S','U','w','W','x','X','y','Y','Z']
            for format_string in strftime_format_strings:
                value = time.strftime(
                    '%{format_string}'.format(format_string=format_string),
                    current_gmtime)
                
                variables[format_string] = value
                
                try:
                    variables[format_string] = int(variables[format_string])
                except ValueError:
                    continue
            
            aeval = asteval.Interpreter()
            
            new_event_states = {}
            
            for i,event in enumerate(events):
                try:
                    if event is None:
                        continue
                    if not isinstance(event,(dict,)):
                        continue
                    if 'condition' not in event:
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
                    
                    formated_condition = condition.format(**variables)
                    
                    aeval.symtable = dict(variables)
                    event_state1 = aeval(formated_condition)
                    print '({condition})   ====>   {event_state1}'.format(condition=formated_condition,
                                                                          event_state1=event_state1)

                    new_event_states[event_str] = event_state1
                    
                    assert event_str in new_event_states

                    if not isinstance(event_state1,(bool)):
                        raise CronitorRuleException('Condition did not evaluate to boolean: ' + condition)
                    
                    if event_state1:
                        if event_state0 is None:
                            #print 'state has just initialized'
                            continue
                        if event_state0:
                            #print 'condition is true, but unchanged'
                            continue
                            
                        fire_action(event,subreddit,variables)
                    
                    
                except praw.errors.APIException as e:
                    print >> sys.stderr, 'Exception during handling event:',e
                    traceback.print_exc(file=sys.stderr)
                except Exception as e:
                    print >> sys.stderr, 'Exception during handling event:',e
                    traceback.print_exc(file=sys.stderr)
            event_states = new_event_states
            
            #see if the 1st comment is the help header, make it the help header if necessary
            new_event_strs, update_control_page = update_help_header(new_event_strs, update_control_page)
            
            
        except Exception as e:
            print >> sys.stderr, 'Exception during handling event:',e
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
