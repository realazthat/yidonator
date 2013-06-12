#!/usr/bin/python
# -*- coding: utf-8 -*-
import traceback,sys
import socket
import random
import time
import os
import unittest
import re

import requests
import json
from pprint import pprint


"""
from https://gist.github.com/1595135

Written by Christian Stigen Larsen, http://csl.sublevel3.org
Placed in the public domain by the author, 2012-01-11
"""
def ip_int_from_string(s):
    "Convert dotted IPv4 address to integer."
    return reduce(lambda a,b: a<<8 | b, map(int, s.split(".")))

def ip_int_to_string(ip):
    "Convert 32-bit integer to dotted IPv4 address."
    return ".".join(map(lambda n: str(ip>>n & 0xFF), [24,16,8,0]))


def format_relative_time(t):
    
    minute_seconds = 60
    hour_seconds = minute_seconds * 60
    day_seconds = hour_seconds * 24
    week_seconds = day_seconds * 7
    year_seconds = day_seconds * 365
    
    if t < minute_seconds:
        return '{seconds} seconds'.format(seconds=t)
    elif t < hour_seconds:
        return '{minutes} minutes'.format(minutes=int(t/minute_seconds))
    elif t < day_seconds:
        hours = int(t/hour_seconds)
        minutes = int((t - (hours*hour_seconds)) / minute_seconds)
        return '{hours} hours {minutes} minutes'.format(hours=hours,minutes=minutes)
    elif t < year_seconds:
        days = int(t/day_seconds)
        hours = int((t - (days*day_seconds)) / hour_seconds)
        return '{days} days {hours} hours'.format(days=days,hours=hours)
        
    years = int(t/year_seconds)
    weeks = int((t - (years*year_seconds)) / week_seconds)
    return '{years} years {weeks} weeks'.format(years=years,weeks=weeks)
    
 

class IPLocator:
    def __init__(self,config):
        self.config = config
        
        try:
            import pygeoip
            self.gic = pygeoip.GeoIP(config['geoipcityip4_path'])
        
        except Exception as e:
            print >> sys.stderr, 'pygeoip setup error',e
        
    def obtain_locations(self,ip):
        pass

def obtain_address_info(host,config,iplocate=True,rdns=True):
    
    results = {}
    

    ip = None
    #print >> sys.stderr, 'host:',host
    try:
        data = socket.gethostbyname(host)
        #ip = repr(data)
        ip = data
        
        #print 'ip:',ip
    except Exception:
        raise
    
    results['ip'] = ip

    if iplocate:
        results['iplocations'] = {}
        try:
            import urllib
            import json
            
            #FIXME: does this need to be cleaned up??
            rresponse = urllib.urlopen('http://api.hostip.info/get_json.php?ip={ip}&position=true'.format(ip=ip)).read()
                
            
            rresponse_json = json.loads(rresponse)
            #print 'rresponse_json:',rresponse_json
            
            country_name = rresponse_json['country_name']
            country_name = None if country_name is None else country_name.encode('utf-8')
            city = rresponse_json['city']
            city = None if city is None else city.encode('utf-8')
            lng = rresponse_json['lng']
            lat = rresponse_json['lat']
            
            response = (
                '|hostip| country: "{country}" city: "{city}" longitude: {longitude} latitude: {latitude}'.format(
                    country=country_name,
                    city=city,
                    longitude=lng,
                    latitude=lat))
            results['iplocations']['hostip'] = response
            
            
        except Exception as e:
            print >> sys.stderr, 'hostip error:',e
            results['iplocations']['hostip'] = '|hostip| error'
            
        
        try:
            import pygeoip
            gic = pygeoip.GeoIP(config['geoipcityip4_path'])
            
            record = gic.record_by_addr(ip)
            
                    
            response = ('|geoipcityip4| ' + str(record))
            
            results['iplocations']['geoipcityip4'] = response
        except Exception as e:
            print >> sys.stderr, 'pygeoip error',e
            results['iplocations']['geoipcityip4'] = '|geoipcityip4| error'
        
        try:
            ip_int = ip_int_from_string(ip)
            
            #print >> sys.stderr, 'ip_int:',ip_int

            with open(config['IpToCountry.csv']) as ip2country:
                for line in ip2country:
                    line = line.strip()
                    line_data = line.split(',')
                    if len(line) == 0:
                        continue
                    if line[0] == '#':
                        continue
                    
                    """
                    print 'line:',line
                    print 'line_data:',line_data
                    print 'len(line_data):',len(line_data)
                    """
                    start_str = line_data[0].strip()[1:-1]
                    end_str = line_data[1].strip()[1:-1]
                    """
                    print 'start_str:',start_str
                    print 'end_str:',end_str
                    print
                    """
                    ip_first_int = int(start_str)
                    ip_last_int = int(end_str)
                    if ip_first_int <= ip_int and ip_int <= ip_last_int:
                        
                        #print line_data
                        registry = line_data[2].strip()[1:-1]
                        country = line_data[6].strip()[1:-1]
                        ip_first = ip_int_to_string(ip_first_int)
                        ip_last = ip_int_to_string(ip_last_int)
                        
                        response = ('|IpToCountry| range:[{ip_first}-{ip_last}], registry: {registry}, country: {country}'.format(
                                ip_first=ip_first,ip_last=ip_last,registry=registry,country=country))
                        
                        results['iplocations']['IpToCountry'] = response
                        
                        break
                results['iplocations']['IpToCountry'] = '|IpToCountry| error, no results'
        except Exception as e:
            print >> sys.stderr, 'IpToCountry error:',e
            results['iplocations']['IpToCountry'] = '|IpToCountry| error'
        
    
    
    if rdns:
        results['domains'] = []
        try:
            from dns import resolver,reversename
            addr=reversename.from_address(ip)
            #print >> sys.stderr, addr
            
            for hmm in resolver.query(addr,"PTR"):
                results['domains'] += [str(hmm)]
        except Exception as e:
            
            print >> sys.stderr,  'Reverse DNS error:',e
    
    return results



def get_standard_argparser():
    import argparse
    parser = argparse.ArgumentParser(add_help=True)
    
    parser.add_argument('--delim', metavar='<delimchar>', type=str, nargs='?', help='delimeter, defaults to space', default=' ')
    parser.add_argument('--indelim', metavar='<delimchar>', type=str, nargs='?',
                        help='input delimiter, overrides --delim, defaults to --delim')
    parser.add_argument('--outdelim', metavar='<delimchar>', type=str, nargs='?',
                        help='output delimeter, overrides --delim, defaults to --delim')
    
    parser.add_argument('--quote', metavar='<quotechar>', type=str, nargs='?', help='quote, defaults to \'"\'', default='"')
    parser.add_argument('--inquote', metavar='<quotechar>', type=str, nargs='?',
                        help='input quote, overrides --quote, defaults to --quote')
    parser.add_argument('--outquote', metavar='<quotechar>', type=str, nargs='?',
                        help='output quote, overrides --quote, defaults to --quote')

    
    parser.add_argument('--infile', '-i', metavar='<path>', type=argparse.FileType('rb'), nargs='?',
                        help='input file path, defaults to stdin', default=sys.stdin)
    parser.add_argument('--outfile', '-o', metavar='<path>', type=argparse.FileType('wb'), nargs='?',
                        help='output file path, defaults to stdout', default=sys.stdout)
    
    return parser

def default_headers_cb(tool,headers):

    tool.csvwriter.writerow(headers)
    tool.outfile.flush()
    
def default_row_cb(tool,row,row_data):
    tool.csvwriter.writerow(row)
    tool.outfile.flush()

class GenericTool:
    
    def __init__(self):
        
        self.headers_cb = default_headers_cb
        self.row_cbs = [default_row_cb]
        self.csvwriter = None
        self.infile = None
        self.outfile = None
        self.parser = get_standard_argparser()
        self.parsed_args = None
    
    def parse_args(self):
        self.parsed_args = self.parser.parse_args()
        
    def run(self):
        import csv
        
        parsed_args = self.parsed_args
        
        indelim = parsed_args.delim if parsed_args.indelim is None else parsed_args.indelim
        outdelim = parsed_args.delim  if parsed_args.indelim is None else parsed_args.outdelim
        
        inquote = parsed_args.quote if parsed_args.inquote is None else parsed_args.inquote
        outquote = parsed_args.quote if parsed_args.outquote is None else result.outquote
        
        
        with parsed_args.infile as infile:
            
            outfile = parsed_args.outfile
            
            self.infile = infile
            self.outfile = outfile
            
            csvreader = self.csvreader = csv.reader(infile, delimiter=indelim, quotechar=inquote)
            csvwriter = self.csvwriter = csv.writer(outfile, delimiter=outdelim, quotechar=outquote)
            
            headers = []
            for row in csvreader:
                headers = row
                break
            
            if self.headers_cb is not None:
                self.headers_cb(self,headers)
            
            for row in csvreader:
                try:
                    
                    row_data = {}
                    for idx in range(len(headers)):
                        row_data[headers[idx]] = row[idx]
                    
                    for row_cb in self.row_cbs:
                        try:
                            row_cb(self,row,row_data)
                        except IOError as e:
                            raise
                        except Exception as e:
                            print >> sys.stderr,  'Exception while row_cb:',e
                            print >> sys.stderr,  'row_cb:',row_cb
                            traceback.print_exc(file=sys.stderr)
                
                except IOError as e:
                    raise
                except Exception as e:
                    print >> sys.stderr,  'Exception while parsing line from stdin:',e
                    print >> sys.stderr,  'line:',row
                    
                    traceback.print_exc(file=sys.stderr)


def generate_random_alphanumerics(length):
    
    abcs = 'abcdefghijklmnopqrstuvwxyz'
    result = [abcs[random.randint(0,len(abcs)-1)] for _ in range(length)]
    
    result = ''.join(result)
    return result




def shorten_url(long_url):
    long_url = long_url.encode('utf-8')
    
    
    parameters = {"longUrl": long_url}
    
    
    
    headers = {'Content-Type':'application/json'}
    api_url = 'https://www.googleapis.com/urlshortener/v1/url'
    r = requests.post(api_url,data=json.dumps(parameters),headers=headers)
    
    
    j = json.loads(r.text)
    
    if 'id' not in j or 'longUrl' not in j or j['longUrl'].encode('utf-8') != long_url:
        return long_url
    
    return j['id'].encode('utf-8')
    
def unescape_entities(html):
    
    import HTMLParser
    return HTMLParser.HTMLParser().unescape(html)

def generate_FUZZY_URLP_RE_STR():
    valid_scheme_chars = 'a-zA-Z'
    valid_domain_chars = '\w\\.'
    def _valid_path_chars():
        safe = '\\$\\-_\\.\\+'
        extra = '\!\*\\(\)\,' #removed \\'
        unreserved = '\w'+ safe+extra
        reserved = '\\;/\\?\:\\@\\&\\='
        escape = '\\%'
        xchar = unreserved + reserved + escape
        
        return xchar
    valid_path_chars = _valid_path_chars()
    tlds = ['aero', 'asia', 'biz', 'cat', 'com', 'coop', 'edu', 'gov',
            'info', 'int', 'jobs', 'mil', 'mobi', 'museum', 'name',
            'net', 'org', 'pro', 'tel', 'travel']
    result = ur'((([' + valid_scheme_chars + ']*\:)?//)?' \
        + '[' + valid_domain_chars + ']*' \
        + '\.([a-zA-Z]{2}|' +  '|'.join(tlds) + ')(\\:[\d]*)?/' \
        + '[' + valid_path_chars + ']*' \
        + '(\\#[' + valid_path_chars + ']*)?' + ')'
    return result

def generate_FUZZY_URL_RE_STR():
    valid_scheme_chars = 'a-zA-Z'
    valid_domain_chars = '\w\\.'
    def _valid_path_chars():
        safe = '\\$\\-_\\.\\+'
        extra = '\!\*\\(\)\,' #removed \\'
        unreserved = '\w'+ safe+extra
        reserved = '\\;/\\?\:\\@\\&\\='
        escape = '\\%'
        xchar = unreserved + reserved + escape
        
        return xchar
    valid_path_chars = _valid_path_chars()
    tlds = ['aero', 'asia', 'biz', 'cat', 'com', 'coop', 'edu', 'gov',
            'info', 'int', 'jobs', 'mil', 'mobi', 'museum', 'name',
            'net', 'org', 'pro', 'tel', 'travel']
    
    domain_RE_STR = ur'(\w+(\.\w+)*)'
    path_RE_STR = ur'(/[' + valid_path_chars + '])'
    query_RE_STR = ur'(\?[' + valid_path_chars + '])'
    fragment_RE_STR = ur'(\#[' + valid_path_chars + '])'
    
    """
    TODO:
    * "...so" matches, make sure no two "." in a domain
    * "something.sol" matches something.so
    """
    result = ur'((([' + valid_scheme_chars + ']*\:)?//)?' \
        + '[' + valid_domain_chars + ']*' \
        + '\.([a-zA-Z]{2}|' +  '|'.join(tlds) + ')(\\:[\d]*)?/?' \
        + '[' + valid_path_chars + ']*' \
        + '(\\#[' + valid_path_chars + ']*)?' + ')'
    return result



"""

timeout
    Socket timeout for each test.
tests
    Proxies to test for.
log
    File object to log to.
"""
def test_proxy(ip,port,tests=['HTTP','SOCKS4','SOCKS5'], timeout=20,log=os.devnull):
    import socksocket
    
    str2proxytype = {'SOCKS4':socksocket.PROXY_TYPE_SOCKS4,
                     'SOCKS5':socksocket.PROXY_TYPE_SOCKS5,
                     'HTTP':socksocket.PROXY_TYPE_HTTP}
    proxytype2str = {socksocket.PROXY_TYPE_SOCKS4:'SOCKS4',
                     socksocket.PROXY_TYPE_SOCKS5:'SOCKS5',
                     socksocket.PROXY_TYPE_HTTP:'HTTP'}
                
    for test in tests:
        if test not in str2proxytype:
            #print >> log, 'test:',test,'is unknown, next!'
            continue
        proxytype = str2proxytype[test]
    
        #print >> log, '  trying', test
        
        s = socksocket.socksocket()
        s.settimeout(20)
        try:
            s.setproxy(proxytype=proxytype,addr=ip,port=port,rdns=True)
            s.connect(('google.com',80))
            
            s.sendall( '''GET / HTTP/1.1\r\nHost: google.com\r\n\r\n''' )
            
            start = time.time()
            timeout = s.gettimeout()
            while True:
                b = s.recv(1)
                if len(b):
                    break
                time.sleep(.001)
                if timeout is not None and time.time() - start >= timeout:
                    raise socket.timeout
            #print >> log, 'found one:',proxy,proxytype2str[proxytype]
            return proxytype2str[proxytype]
        except socket.error as e:
            #print >> log, '    socket.error'
            continue
        except socksocket.ProxyError:
            #print >> log, '    socksocket.ProxyError'
            continue
        except Exception as e:
            print >> log, '    UNKNOWN ERROR:',e
            traceback.print_exc(file=sys.stderr)
        finally:
            s.close()
    return None


class URL_RE:
    
    def __init__(self):
        valid_scheme_chars = 'a-zA-Z'
        valid_domain_chars = '\w\\.'
        def _valid_path_chars():
            safe = '\\$\\-_\\.\\+'
            extra = '\!\*\\(\)\,' #removed \\'
            unreserved = '\w'+ safe+extra
            reserved = '\\;/\\?\:\\@\\&\\='
            escape = '\\%'
            xchar = unreserved + reserved + escape
            
            return xchar
        valid_path_chars = _valid_path_chars()
        tlds = ['aero', 'asia', 'biz', 'cat', 'com', 'coop', 'edu', 'gov',
                'info', 'int', 'jobs', 'mil', 'mobi', 'museum', 'name',
                'net', 'org', 'pro', 'tel', 'travel',
                
                'travel', 'xxx', 'post',
                
                'arpa',
                
                u'бг', u'ελ', u'ישראל', u'мкд', u'日本', u'日本国', u'ລາວ', #u'ليبيا'‎,
                ]
        
        self.scheme_RE_STR = ur'([' + valid_scheme_chars + ']*\:)'
        self.domain_RE_STR = ur'(\w+(\.\w+)*)\.([a-zA-Z]{2}|' +  '|'.join(tlds) + ')(\\:[\d]*)?'
        self.path_RE_STR = ur'(/[' + valid_path_chars + ']*)'
        self.query_RE_STR = ur'(\?[' + valid_path_chars + ']*)'
        self.fragment_RE_STR = ur'(#[' + valid_path_chars + ']*)'
        
        self.domain_RE = re.compile(self.domain_RE_STR)

        
        self.url_RE_STR = u'(^|\s)(({scheme}?//)?({domain})({path})?({query})?({fragment})?)($|\s)'
        self.url_RE_STR = self.url_RE_STR.format(scheme=self.scheme_RE_STR,
                                                 domain=self.domain_RE_STR,
                                                 path=self.path_RE_STR,
                                                 query=self.query_RE_STR,
                                                 fragment=self.fragment_RE_STR).encode('utf-8')
        self.url_RE = re.compile(self.url_RE_STR)

class TestURL_RE(unittest.TestCase):

    def setUp(self):
        self.url_re = URL_RE()

    def test_domain_two_dots(self):
        
        self.assertIsNotNone(self.url_re.url_RE.search('a.com'))
        self.assertIsNone(self.url_re.url_RE.search('a..com'))
        
    def test_invalid_tld(self):
        
        self.assertIsNotNone(self.url_re.url_RE.search('a.co'))
        self.assertIsNone(self.url_re.url_RE.search('a.cod'))
        
        
    def test_urls(self):
        
        urls = [
                ('google.com', True),
                ('google..com', False),
                ('google.comp', False),
                ('google.cop', False),
                ('//google.com', True),
                ('mmm://google.com', True),
                ('google.com/', True),
                ('google.com/?', True),
                ('google.com/?#', True),
                ('google.com/#', True),
                ('google.com?', True),
                ('google.com?#', True),
                ('google.com#', True),
                ('mmm..........chummus.com', False),
                ]
        for url, expectation in urls:
            print 'url:',url
            
            if expectation:
                self.assertIsNotNone(self.url_re.url_RE.search(url))
            else:
                self.assertIsNone(self.url_re.url_RE.search(url))
        
        
def main():
    unittest.main()


if __name__ == "__main__":
    main()

