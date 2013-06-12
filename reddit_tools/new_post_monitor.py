
import traceback,sys, requests,json
import urllib2
import collections

class NewSomethingMonitor:
    
    def __init__(self, subreddit, limit_per_query, user_agent, logfile, request_url):
        self.subreddit = subreddit
        self.limit_per_query = limit_per_query
        self.user_agent = user_agent
        self.logfile = logfile
        self.request_url = request_url
        
        self.cbs = []
        
        self.last_100_names = collections.deque([])
        
        self.last_100_names_set = set()
        
        

        
    def _obtain_last(self,limit,before=None):
        
        parameters={}
        
        parameters['limit'] = limit
        
        
        if before is not None:
            parameters['before'] = before
        
            
        
        url = 'http://www.reddit.com/r/{sr}/{top}.json'.format(sr=self.subreddit,top='new')
        
        headers = {'User-agent': self.user_agent}
        #print 'url:',url
        r = requests.get(url,params=parameters)
        j = json.loads(r.text)
    
        """
        params = '&'.join([ '{name}={value}'.format(name=name,value=value) for (name,value) in parameters.iteritems() ])
        
        url = '{url}?{params}'.format(url=url,params=params)
        #print >> self.logfile, 'url:',url
        r = urllib2.Request(url=url,headers=headers)
        r = urllib2.urlopen(r).read()
        j = json.loads(r)
        """
        
        return j
    
    def _check_has_new_post(self):
        j = self._obtain_last(limit=1,before=None)
        
        if len(j['data']['children']) == 0:
            return False
        
        latest_post_name = j['data']['children'][0]['data']['name']
        if latest_post_name != self.get_lastname():
            return True
        return False
    def get_lastname(self):
        
        if len(self.last_100_names) == 0:
            return None
        
        return self.last_100_names[-1]
    
    def name_count(self):
        return len(self.last_100_names)
    
    def record_name(self,name):
        assert len(self.last_100_names) == len(self.last_100_names_set)
        if name in self.last_100_names_set:
            return
        
        if len(self.last_100_names) >= 100:
            oldname = self.last_100_names.popleft()
            self.last_100_names_set.discard(oldname)
            assert len(self.last_100_names) == len(self.last_100_names_set)
        
        self.last_100_names.append(name)
        self.last_100_names_set.add(name)
        
        
        assert len(self.last_100_names) == len(self.last_100_names_set)
        
    def discard_top_name(self):
        assert len(self.last_100_names) == len(self.last_100_names_set)
        if len(self.last_100_names) == 0:
            return
        
        topname = self.last_100_names.pop()
        self.last_100_names_set.discard(topname)
        
        assert len(self.last_100_names) == len(self.last_100_names_set)
    
    
    def has_name(self,name):
        return name in self.last_100_names_set
    
    def run(self):
        
        if self.get_lastname() is None:
            j = self._obtain_last(limit=1,before=None)
            
            if len(j['data']['children']) > 0:
                self.record_name(j['data']['children'][0]['data']['name'])
            
            return
        
        has_new_post = self._check_has_new_post()
        
        if not has_new_post:
            return
        
        j = self._obtain_last(limit=self.limit_per_query,before=self.get_lastname())
        
        if len(j['data']['children']) == 0:
            self.discard_top_name()
            return
        
        
        for new_post in reversed(j['data']['children']):
            name = new_post['data']['name']
        
            self.record_name(name)
        
            for cb in self.cbs:
                
                try:
                    cb(new_post)
                except Exception as e:
                    print >> self.logfile, 'Exception during new_something_cb():',e
                    traceback.print_exc(file=self.logfile)            

class NewPostMonitor(NewSomethingMonitor):
    def __init__(self, subreddit, limit_per_query, user_agent, logfile=sys.stderr):
        url = 'http://www.reddit.com/r/{sr}/{top}.json'.format(sr=subreddit,top='new')
        
        NewSomethingMonitor.__init__(self, subreddit, limit_per_query,
                                     user_agent, logfile,
                                     request_url=url)
    
