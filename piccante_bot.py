import argparse
import datetime
import itertools as itt
import json
import re
import sys

import bs4
import requests

PY2 = sys.version_info[0] == 2

menu_url = ('http://www.s-bar.de/ihr-betriebsrestaurant/'
            'aktuelle-speiseplaene.html')

daily_url = ('http://www.s-bar.de/ihr-betriebsrestaurant/'
             'aktuelle-speiseplaene/piccante-tagesangebot.html')

day_regex = re.compile(r'\s?\w+,\ (\d\d)\.\s\w+\s20\d\d\s', re.UNICODE)
additives_regex = re.compile(r'\s\([A-Z0-9,\s]+\)\s?', re.UNICODE)
daily_regex = re.compile(r'[A-Z][^a-z].*', re.UNICODE)


def zip_longest(*args, **kwargs):
    if PY2:
        return itt.izip_longest(*args, **kwargs)
    else:
        return itt.zip_longest(*args, **kwargs)


# Grabbed directly from itertools recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return zip_longest(fillvalue=fillvalue, *args)


def format_menu(date, dishes):
    """ Format a datetime and a list of dishes as a markdown message. """
    # https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
    menu = u"*Today's lunch:* {0:%A}".format(date)
    for d in dishes:
        menu += u'\n\u2022 {}'.format(d)
    return menu


def weekly(date):
    """ Get list of dishes from weekly menu. """
    # Get and parse html
    req = requests.get(menu_url)
    soup = bs4.BeautifulSoup(req.text, 'html.parser')
    # Find menu section
    menu_parent = soup.find(id='c840').find(class_="csc-textpic-text")
    # Remove cruft and join into one big string
    # Necessary because of messy html
    menu_string = ' '.join(itt.takewhile(
        lambda s: 'Die aktuelle Speisekarten' not in s,
        menu_parent.stripped_strings))
    # Extract day and dishes into dict
    days_dishes = grouper(day_regex.split(menu_string)[1:], 2)
    menu = {int(day): dishes for day, dishes in days_dishes}
    # Get day's dishes and separate using additives list
    return additives_regex.split(menu[date.day])[:-1]


def daily():
    """ Get list of dishes from daily menu. """
    req = requests.get(daily_url)
    soup = bs4.BeautifulSoup(req.text, 'html.parser')
    # Find daily dishes section
    menu_parent = soup.find(id='c937').find(class_="csc-textpic-text")
    # Get all string in list items
    items = (i.string for i in menu_parent.find_all('li'))
    # Strip off abbreviated info and additives
    dishes = (daily_regex.split(i)[0] for i in items)
    return list(dishes)


def post(hook_url):
    today = datetime.datetime.now()
    menu = format_menu(today, weekly(today) + daily())
    return requests.post(hook_url, data=json.dumps({'text': menu}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Post today's lunch menu to Slack.")
    parser.add_argument('hook', metavar='URL', type=str,
                        help='The Slack WebHook URL.')
    args = parser.parse_args()
    post(args.hook).raise_for_status()
