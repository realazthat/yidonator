#!/usr/bin/python

import praw
import time
import requests
import json
import re
import sys,traceback
import operator
from datetime import datetime

from pprint import pprint

from tool_utils import shorten_url, unescape_entities

from reddit_tools.new_post_monitor import NewPostMonitor
from reddit_tools.new_comment_monitor import NewCommentMonitor 

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
    def __init__(self, r, subreddit, rules, contributors, moderators):
        self.r = r
        self.subreddit = subreddit
        self.rules = rules
        
        
        self.contributors = contributors
        self.moderators = moderators
        
        self.post_count = 0
        self.acted_count = 0
    
    def apply_rules(self,subject_info):
        
        user_info = {}
        
        
        
        for rule in self.rules:
            success = self.apply_rule(rule,subject_info,user_info)
            if success:
                self.acted_count += 1
        
        
    def apply_rule(self,rule,subject_info,user_info):
    
        kind = None
        if subject_info['kind'] == 't3':
            kind == 'submission'
        elif subject_info['kind'] == 't1':
            kind == 'comment'
        else:
            assert False
        
        if rule.post_type != 'both':
            if rule.post_type != kind:
                return False
        
        
        num_reports = subject_info['reports']
        if num_reports is None:
            num_reports = 0
        if num_reports < rule.reports:
            return False
        
        if rule.is_reply is not None:
            #TODO
            assert False and "TODO"
        
        user = subject_info['user']
        
        if len(user_info) == 0:
            
            redditor = self.r.get_redditor(user)
            
            account_age = datetime.utcfromtimestamp(time.time()) - datetime.utcfromtimestamp(redditor.created_utc)
        
            user_info['account_age'] = account_age.days
            user_info['link_karma'] = redditor.link_karma
            user_info['comment_karma'] = redditor.comment_karma
            user_info['combined_karma'] = redditor.link_karma + redditor.comment_karma
            user_info['is_gold'] = redditor.is_gold
            
            #TODO
            user_info['is_shadowbanned'] = False
            #user_info['is_shadowbanned'] = redditor.is_shadowbanned
            
            user_info['rank'] = 'user'
            
            if user in self.contributors:
                user_info['rank'] = 'contributor'
            elif user in self.moderators:
                user_info['rank'] = 'moderator'
            
        
        
        satisfied_any = False if len(rule.user_conditions) != 0 else True
        for user_condition in rule.user_conditions:
            
            
            if user_condition(user_info):
               satisfied_any = True
               if rule.must_satisfy == 'any':
                   break
            else:
                if rule.must_satisfy == 'all':
                    return False
        
        if not satisfied_any:
            return False
        
        results = []
        for condition in rule.conditions:
            result = condition(subject_info)
            
            if result is None:
                return False
                
            results += result
        
        if len(results) == 0:
            return False
        
        for action in rule.actions:
            try:
                action(subject_info,results)
            except Exception as e:
                
                print >> sys.stderr, 'exception while performing action',action,'e:',e
                traceback.print_exc(file=sys.stderr)            
        
        
        self.acted_count += 1
        return True
        
    
    def collect_post(self,jpost):
        self.post_count += 1
        
        
        subject_info = {}
        subject_info['domain'] = unescape_entities(jpost['data']['domain'])
        subject_info['url'] = unescape_entities(jpost['data']['url'])
        subject_info['body'] = unescape_entities(jpost['data']['selftext'])
        subject_info['permalink'] = unescape_entities(jpost['data']['permalink'])
        subject_info['user'] = unescape_entities(jpost['data']['author'])
        subject_info['title'] = unescape_entities(jpost['data']['title'])
        subject_info['kind'] = jpost['kind']
        subject_info['reports'] = jpost['data']['num_reports']
        subject_info['subreddit'] = self.subreddit.display_name
        subject_info['link_id'] = jpost['data']['name']
        
        self.apply_rules(subject_info)
        
    def collect_comment(self,jpost):
        self.post_count += 1
        
        
        subject_info = {}
        subject_info['domain'] = unescape_entities(jpost['data']['domain'])
        subject_info['url'] = unescape_entities(jpost['data']['url'])
        subject_info['body'] = unescape_entities(jpost['data']['selftext'])
        subject_info['permalink'] = unescape_entities(jpost['data']['permalink'])
        subject_info['user'] = unescape_entities(jpost['data']['author'])
        subject_info['title'] = unescape_entities(jpost['data']['title'])
        subject_info['kind'] = jpost['kind']
        subject_info['reports'] = jpost['data']['num_reports']
        subject_info['subreddit'] = self.subreddit.display_name
        subject_info['link_id'] = jpost['data']['id']
        
        self.apply_rules(subject_info)
    def run(self):
        

        
        print >> sys.stderr, 'processed {n} posts with {m} positive results.'.format(n=self.post_count,
                                                                                     m=self.acted_count)

        self.post_count = 0
        self.acted_count = 0



"""
class AndCondition:
    def __init__(self,conditions):
        self.conditions = conditions
    def __call__(self,item):
        
        for condition in self.conditions:
            result = condition(item)
            
        return True

class OrCondition:
    def __init__(self,conditions):
        self.conditions = conditions
    def __call__(self,item):
        
        for condition in self.conditions:
            result = condition(item)
            if result is not None:
                return result
        return False
"""

class FieldMatchCondition:
    def __init__(self,subjects,matches,match_type):
        assert isinstance(subjects, list)
        self.subjects = subjects
        self.matches = matches
        self.match_type = match_type
    
    
    def __call__(self,subject_values):
        
        results = []
        for subject in self.subjects:
            subject_value = subject_values[subject].lower()
            for match_test in self.matches:
                assert match_test is not None
                
                if self.match_type == 'full-exact':
                    if match_test == subject_value:
                        results += [match_test]
                elif self.match_type == 'full-text':
                    subject_value_text = subject_value.strip(string.punctuation+string.whitespace)
                    
                    if match_test == subject_value_text:
                        results += match_test
                elif self.match_type == 'includes-word':
                    
                    words = subject_value.split(' ')
                    
                    if match_test in words:
                        results += [match_test]
                elif self.match_type == 'includes':
                    
                    if match_test in subject_value:
                        results += [match_test]
                elif self.match_type == 'domain-special':
                    
                    if match_test == subject_value or subject_value.endswith('.' + match_test):
                        results += [match_test]
                    
                else:
                    #TODO regex
                    assert False
        
        if len(results) == 0:
            return None
        
        return results

    def __str__(self):
        
        return str({'subjects': str(self.subjects),
                    'matches': str(self.matches),
                    'match_type': self.match_type})
    def __repr__(self):
        
        return self.__str__()
        
class UserConditionComparison:
    def __init__(self,op,field,compareto):
        self.op = op
        self.field = field
        self.compareto = compareto
    
    def __call__(self,user_info):
        
        return self.op(user_info[self.field],self.compareto)
        
    def __str__(self):
        
        return str({'op': str(self.op), 'field':self.field, 'compareto': self.compareto})
    def __repr__(self):
        
        return self.__str__()

        

class PrawAction:
    def __init__(self,subreddit, action):
        self.subreddit = subreddit
        self.action = action
    
    def __call__(self,post_info,results):
        
        link_id = post_info['link_id']
        
        if post_info['kind'] == 't3':
            submission = self.subreddit.reddit_session.get_submission(submission_id=link_id)
            self.act(post_info,results,submission)
        elif post_info['kind'] == 't1':
            
            comment = self.subreddit.reddit_session.get_comment(comment_id=link_id)
            self.act(post_info,results,comment)
        else:
            assert False

    def act(self,post_info,results,post):
        assert False and "IMPEMENT THIS"
        
    def __str__(self):
        sr = self.subreddit.display_name
        
        return str( { 'action': self.action, 'subreddit': sr } )
        
        
    def __repr__(self):
        return self.__str__()

class ApproveAction(PrawAction):
    def __init__(self,subreddit):
        PrawAction.__init__(self,subreddit,'approve')
        
    def act(self,post_info,results,post):
        post.approve()


class SpamAction(PrawAction):
    def __init__(self,subreddit):
        PrawAction.__init__(self,subreddit,'spam')
        
    def act(self,subject_info,results,post):
        post.spam()

class RemoveAction(PrawAction):
    def __init__(self,subreddit):
        PrawAction.__init__(self,subreddit,'remove')
    
    def act(self,post_info,results,post):
        post.remove()

class ReportAction(PrawAction):
    def __init__(self,subreddit):
        PrawAction.__init__(self,subreddit,'report')
    
    def act(self,post_info,results,post):
        post.report()
        
class ModMailAction:
    def __init__(self,subreddit,subject,comment):
        
        
        self.r = subreddit.reddit_session
        self.subreddit = subreddit
        self.subject = subject
        self.comment = comment
    
    def __call__(self,post_info,results):
        
        permalink = 'http://www.reddit.com{permalink}'.format(permalink=post_info['permalink'])

        self.r.send_message('/r/'+self.subreddit.name,
                            self.subject,
                            permalink+'\n\n'+self.comment)

class AuthorMailAction:
    def __init__(self,subreddit,subject,comment):
        
        
        self.r = subreddit.reddit_session
        self.subreddit = subreddit
        self.subject = subject
        self.comment = comment
    
    def __call__(self,post_info,results):
        
        permalink = 'http://www.reddit.com{permalink}'.format(permalink=post_info['permalink'])

        self.r.send_message('/u/'+ post_info['user'],
                            self.subject,
                            permalink+'\n\n'+self.comment)

class PostCommentAction:
    def __init__(self,subreddit,subject,comment):
        
        
        self.r = subreddit.reddit_session
        self.subreddit = subreddit
        self.subject = subject
        self.comment = comment
    
    def __call__(self,post_info,results):
        
        if post_info['kind'] == 't1':
            rcomment = self.r.get_comment(comment_id=post_info['link_id'])
            rcomment.reply(self.comment).distinguish()
        elif post_info['kind'] == 't3':
            
            submission = self.r.get_submission(submission_id=post_info['link_id'])
            submission.add_comment(self.comment).distinguish()
        
        
    

class ModitorException(Exception):
    pass

class InvalidSubjectError(ModitorException):
    
    def __init__(self,subject):
        ModitorException.__init__(self,'{subject} is not a valid subject,'
            'see https://github.com/Deimos/AutoModerator/wiki/Wiki-Configuration#allowed-match-subjects'
            ' for list of valid subjects.'.format(subject=subject))

class InvalidUserCondition(ModitorException):
    
    def __init__(self,subject,value):
        ModitorException.__init__(self,'\'{subject}: {value}\' is not a valid User Condition,'
            'see https://github.com/Deimos/AutoModerator/wiki/Wiki-Configuration#user-conditions'
            ' for list of User Conditions.'.format(subject=subject,value=value))

    
class Rule:
    def __init__(self):
        self.user_conditions = []
        self.conditions = []
        self.actions = []
        self.post_type = 'both'
        self.reports = 0
        self.is_reply = None
    
    def __str__(self):
        return str(vars(self))
    def __repr__(self):
        return str(vars(self))
        
    
def parse_rules(rule_configs,subreddit):

    subjects = set(['title', 'domain', 'url', 'user', 'body',
                'media_user', 'media_title',
                'media_description', 'author_flair_text',
                'author_flair_css_class', 'link_id'])
    
    default_match_type = {
        'title': None,
        'domain':'domain-special',
        'url':'includes',
        'user':'full-exact',
        'body': None,
        'text': None,
        'media_user': 'full-exact',
        'media_title': None,
        'media_description': None,
        'author_flair_text':'full-exact',
        'author_flair_css_class':'full-exact',
        'link_id':'full-exact',
        
        }
    valid_user_conditions = set(['account_age','link_karma','comment_karma',
        'combined_karma','is_gold','is_shadowbanned','rank','must_satisfy'])
    flair_actions = set(['link_flair_text', 'link_flair_class',
        'user_flair_text', 'user_flair_class'])
    
    valid_actions = set(['approve','remove','spam','report'])
    valid_rule_types = set(['comment','submission','both'])
    
    def handle_error_gracefully(moditorexception):
        #TODO
        raise moditorexception
        
    
    subject2conditions = {}
    
    rules = []
    for rule_config in rule_configs:
        if rule_config is None:
            continue
    
        rule = Rule()
        rules += [rule]
        
        
        for key,value in rule_config.iteritems():
            if '+' in key:
                
                values = value
                if not isinstance(value,list):
                    values = [value]
                
                subject_keys = key.split('+')
                
                for subject_key in subject_keys:
                    if len(subject_key) == 0:
                        continue
                    
                    if subject_key not in subjects:
                        handle_error_gracefully(InvalidSubjectError(subject_key))
                        continue
                match_type = 'includes-word'
                
                condition = FieldMatchCondition(subject_keys,values,match_type)
                
                subject2conditions[key] = [condition]
                continue
            
            elif key in subjects:
                values = value
                if not isinstance(value,list):
                    values = [value]
                
                subject = key
                
                match_type = default_match_type[subject]
                
                if match_type is None:
                    match_type = 'includes-word'
                
                condition = FieldMatchCondition([subject],values,match_type)
                
                rule.conditions += [condition]
                
                subject2conditions[subject] = [condition]
                continue
                
                
                
            elif key == 'user_conditions':
                
                if not isinstance(value,dict):
                    handle_error_gracefully(ModitorException('User conditions are invalid, see https://github.com/Deimos/AutoModerator/wiki/Wiki-Configuration#user-conditions for examples on correct user conditions'))
                    continue
                
                for subject,condition in value.iteritems():
                    
                    if subject not in valid_user_conditions:
                        handle_error_gracefully(InvalidUserCondition(subject,condition))
                    
                    if subject == 'must_satisfy':
                        if condition not in set(['any','all']):
                            handle_error_gracefully(InvalidUserCondition(subject,condition))
                            continue
                        
                        rule.must_satisfy = condition
                        
                        continue
                    
                    try:
                        op = None
                        if subject.startswith('is_'):
                            op = operator.eq
                            condition = bool(condition)
                        elif condition.startswith('<'):
                            op = operator.lt
                            condition = int(condition[1:].strip())
                        elif condition.startswith('>'):
                            op = operator.gt
                            condition = int(condition[1:].strip())
                        rule.user_conditions += [UserConditionComparison(op,subject,condition)]
                    except ValueError:
                        handle_error_gracefully(InvalidUserCondition(subject,condition))
                        continue
                    
                    
                continue
            
            elif key in flair_actions:
                #TODO flair_actions
                continue
            elif key == 'type':
                
                if value not in valid_rule_types:
                    handle_error_gracefully( ModitorException(
                        '{value} is not a valid filter type. type must be one of' \
                        ' \'comment\', \'submission\' or \'both\'.'.format(value=value)))
                    continue
                rule.post_type = value
                continue
            elif key == 'reports':
                if not isinstance(value,(int)):
                    handle_error_gracefully( ModitorException(
                        '{value} is not a valid integer. report key expects an integer'.format(value=value)))
                    continue
                rule.reports = value
            elif key == 'is_reply':
                
                if not isinstance(value,(bool)) and str(value) in ('True','False'):
                    handle_error_gracefully( ModitorException(
                        '{value} is not a valid boolean. is_reply key expects an boolean'.format(value=value)))
                
                    continue
                rule.is_reply = value
                continue
            elif key == 'action':
                if not isinstance(value,list):
                    value = [value]
                
                
                for action in value:
                    if action not in valid_actions:
                        handle_error_gracefully( ModitorException(
                            '{action} is not a valid action.'.format(action=action)))
                        continue
                    
                    if action == 'approve':
                        rule.actions += [ApproveAction(subreddit)]
                    elif action == 'remove':
                        rule.actions += [RemoveAction(subreddit)]
                    elif action == 'spam':
                        rule.actions += [SpamAction(subreddit)]
                    elif action == 'report':
                        rule.actions += [ReportAction(subreddit)]
                    
                continue
            elif key == 'comment' or key == 'message' or key == 'modmail':
                
                recipient = None
                
                subject = 'Moditor match'
                
                comment = value
                
                if key == 'modmail':
                    rule.actions += [ModMailAction(subreddit,subject,comment)]
                elif key == 'message':
                    rule.actions += [AuthorMailAction(subreddit,subject,comment)]
                elif key == 'comment':
                    rule.actions += [PostCommentAction(subreddit,subject,comment)]
                    
                continue
            else:
                handle_error_gracefully(InvalidSubjectError(key))
                continue
            
    
        for key,value in rule_config.iteritems():
            if key == 'modifiers':
                modifiers = value
                if not isinstance(value, dict):
                    
                    assert False and "TODO"
                else:
                
                    for subject,modifier in modifiers.iteritems():
                        
                        assert False and "TODO"
                
                
                #TODO add modifiers
                
                continue
    return rules

def main():
    
    import yaml
    
    import argparse
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('config', type=argparse.FileType('r'),help="configuration file")

    parsed_args = parser.parse_args()

    config_file = parsed_args.config

    #config = {}

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
    #subreddit = config['subreddit']
    control_page_name = config['control_page']
    
    r = praw.Reddit(user_agent=user_agent)
    r.login(config['reddit_user'],config['reddit_pwd'])
    
    subreddit = r.get_subreddit(config['subreddit'])
    
    
    try:
        
        moderators = subreddit.get_moderators()
        moderators = set([moderator.name for moderator in moderators])
        
        #print vars(subreddit)
        
        contributors = set([])
        
        if config['reddit_user'] in moderators:
            contributors = subreddit.get_contributors()
            contributors = set([contributor.name for contributor in contributors])
        
        
        #wiki_control_page = subreddit.get_wiki_page(control_page_name)
        #wiki_config_data = wiki_control_page.content_md
        
        wiki_config_data = \
'''
---
    title: the
    user_conditions:
        must_satisfy: any
        comment_karma: "< 10"
        account_age: "< 7"
    modmail: 'test detection'
---'''
    
        
        
        rule_configs = yaml.load_all(wiki_config_data)
        
        
        rules = parse_rules(rule_configs,subreddit)
        
        for rule in rules:
            
            print
            pprint(rule)
            
        #exit()
    
        
        
        new_comment_monitor = NewCommentMonitor(subreddit, limit_per_query, user_agent)
        new_post_monitor = NewPostMonitor(subreddit, limit_per_query, user_agent)
        
        collector = Collector(r, subreddit, rules, contributors, moderators)
        
        
        
        new_comment_monitor.cbs += [collector.collect_comment]
        new_post_monitor.cbs += [collector.collect_post]
        
        services = [
            
            new_comment_monitor.run,
            new_post_monitor.run,
            collector.run,
            ]
        
        
        while True:
            
            for service in services:
                try:
                    service()
                except Exception as e:
                    
                    print >> sys.stderr, 'Exception during new_post_cb():',e
                    traceback.print_exc(file=sys.stderr)            
            
            time.sleep(loop_time)
            

    except ModitorException as e:
        raise e
        #TODO pm mods and continue
        pass
        
    
    
    
    
    
if __name__ == "__main__":
    main()

