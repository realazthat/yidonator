#! /usr/bin/env python

import praw
import yaml
import argparse

class FlairCollector:

	def __init__(self, r, subreddit):
		self.r = r
		self.subreddit = subreddit

	def get_flair_counts(self):
		flair_count_dict = {}
		flair_list = self.subreddit.get_flair_list()
		for item in flair_list:
			f = item['flair_text']
        	        if f in flair_count_dict.keys():
				current_count = flair_count_dict[f]
			else: current_count = 0
			flair_count_dict[f] = current_count + 1
		return flair_count_dict

def main():
	parser = argparse.ArgumentParser(add_help=True)
	parser.add_argument('config', type=argparse.FileType('r'), help="configuration_file")
	parsed_args = parser.parse_args()
	config_file = parsed_args.config

	try:
		config = yaml.load(config_file)
	except:
		print >> sys.stderr, '\nError: parsing configuration\n'
		raise

	user_agent = config['user_agent']
	loop_time = config['loop_time']
	limit_per_query = 50

	r = praw.Reddit(user_agent=user_agent)
	r.login(config['reddit_user'], config['reddit_pwd'])

	subreddit = r.get_subreddit(config['subreddit'])
	
	flair_collector = FlairCollector(r, subreddit)
	flairs = flair_collector.get_flair_counts()
	print len(flairs)

if __name__ == "__main__":
	main()
