
import traceback,sys, requests,json

"""
class NewCommentMonitor:
    
    def __init__(self, subreddit, limit_per_query, user_agent, logfile=sys.stderr):
        self.subreddit = subreddit
        self.limit_per_query = limit_per_query
        self.user_agent = user_agent
        self.logfile = logfile
        
        self.new_comment_cbs = []
        self.before = None

    def run(self):
                
        
        parameters = {}
        
        if self.before is not None:
            parameters['before'] = self.before
            parameters['limit'] = self.limit_per_query
        else:
            parameters['limit'] = 1
        
        headers = {'User-agent': self.user_agent}
        
        r = requests.get('http://www.reddit.com/r/{sr}/comments.json'.format(sr=self.subreddit),
                         headers=headers,
                         params=parameters)

        j = json.loads(r.text)
        
    
        def set_before():
            if len(j['data']['children']) != 0:
                first_post_kind = j['data']['children'][0]['kind']
                first_post_id = j['data']['children'][0]['data']['id']
            
                self.before = '{kind}_{post_id}'.format(kind=first_post_kind,post_id=first_post_id)
        
        if self.before is None:
            set_before()
            return
        
        
        set_before()
        
        for comment in j['data']['children']:
            
            try:
                for cb in self.new_comment_cbs:
                    try:
                        cb(comment)
                    except Exception as e:
                        print >> self.logfile, 'exception during comment callback handling:',e
                        traceback.print_exc(file=self.logfile)
                        continue
                    
            except Exception as e:
                print >> self.logfile, 'exception during comment handling:',e
                traceback.print_exc(file=self.logfile)
                continue
        """
        
from new_post_monitor import NewSomethingMonitor
class NewCommentMonitor(NewSomethingMonitor):
    def __init__(self, subreddit, limit_per_query, user_agent, logfile=sys.stderr):
        url = 'http://www.reddit.com/r/{sr}/comments.json'.format(sr=subreddit)
        
        NewSomethingMonitor.__init__(self, subreddit, limit_per_query,
                                     user_agent, logfile,
                                     request_url=url)
    


