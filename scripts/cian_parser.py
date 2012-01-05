#!/usr/bin/env python
import os
import sys

# Hardwire in appengine modules to PYTHONPATH
# or use wrapper to do it more elegantly
DIR_PATH = '/home/buger/work/google_appengine'

EXTRA_PATHS = [
  DIR_PATH,
  os.path.join(DIR_PATH, 'lib', 'antlr3'),
  os.path.join(DIR_PATH, 'lib', 'django_0_96'),
  os.path.join(DIR_PATH, 'lib', 'fancy_urllib'),
  os.path.join(DIR_PATH, 'lib', 'ipaddr'),

  os.path.join(DIR_PATH, 'lib', 'webob'),
  os.path.join(DIR_PATH, 'lib', 'yaml', 'lib'),
  os.path.join(DIR_PATH, 'lib', 'simplejson'),
  os.path.join(DIR_PATH, 'lib', 'graphy'),
]

def fix_sys_path():
  """Fix the sys.path to include our extra paths."""
  sys.path = EXTRA_PATHS + sys.path

fix_sys_path()

# Add your models to path
my_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, my_root_dir)

from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.ext.remote_api import remote_api_stub
import getpass

from lib.models import *

APP_NAME = 'russiaflatrent'
os.environ['AUTH_DOMAIN'] = 'gmail.com'
os.environ['USER_EMAIL'] = 'leonsbox@gmail.com'

def auth_func():
    return ("leonsbox@gmail.com", "calestoffs4ic")
    # return (raw_input('Username:'), getpass.getpass('Password:'))

# Use local dev server by passing in as parameter:
# servername='localhost:8080'
# Otherwise, remote_api assumes you are targeting APP_NAME.appspot.com
remote_api_stub.ConfigureRemoteDatastore(APP_NAME,
 '/remote_api', auth_func)

# Do stuff like your code was running on App Engine

from adsparser import *

url = "http://www.cian.ru/cat.php?deal_type=1&currency=2&totime=3600&room0=1&room1=1&room2=1&room3=1&room4=1&obl_id=1&order=4"

import time


class CianAdParser(BaseAdParser):
    def date_format(self):
        return "%d.%m.%y %H:%M"

    def encoding(self):
        return "cp1251"

    def get_title(self):
        return "".join(self.page.findAll('td')[1].findAll(text=True))

    def get_address(self):
        return self.get_title()

    def get_name(self):
        return "cian"

    def get_contact(self):
        return self.page.findAll('td')[8].find('a').string

    def get_price(self):
        return "".join(self.page.findAll('td')[4].findAll(text=True))

    def is_agent(self):
        return True

    def get_content(self):
        return "".join(self.page.findAll('td')[9].findAll(text=True))

    def get_date(self):
        return str(self.page.findAll('td')[9].find('font').string)


def get_list(url, region = 'msk', page = 1):
    time.sleep(15)

    paged_url = url + "&p=%d" % page

    content = MozillaEmulator().download(paged_url)

    content = content.decode("cp1251",'ignore')

    content = BeautifulSoup(content)

    rows = content.find("table", "cat").findAll("tr")

    parse_next_page = True

    ads = []

    for row in rows:
        try:
            parser = CianAdParser(None, region, row).parse()
            parser.url = "http://www.cian.ru/showphoto.php?id_flat=%s" % row['id'].replace('tr_', '')
            print parser.url
        except:
            parser = None

        if parser:
            ad = Ad(key_name = parser.url,
                    title = parser.title,
                    source = parser.get_name(),
                    md5 = parser.md5,
                    contact = parser.contact,
                    phone = parser.phone,
                    price = parser.price,
                    parent_url = url,
                    created_at = parser.date,
                    region = parser.region)

            if parser.address_id:
                ad.address_id = parser.address_id[0]

            if parser.agent:
                ad.rating = 0

            ads.append(ad)

    print "saving ads: %d" % len(ads)
    db.put(ads)
    print "ads saved"

    for ad in ads:
        try:
            taskqueue.add(queue_name = 'quick', url = '/ad/check', params = {'key': ad.key().name() })
        except:
            pass

        print "adding task"

    if parse_next_page:
        print "parsing page %d" % (page+1)
        page = page+1
        get_list(url, region, page+1)

get_list(url)
