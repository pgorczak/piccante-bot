#!/usr/bin/env python

import argparse
import datetime
import itertools as itt
import re

import bs4
import requests


menu_url = ('http://www.s-bar.de/ihr-betriebsrestaurant/'
            'aktuelle-speiseplaene.html')

day_regex = re.compile(r'\s?\w+,\ (\d\d)\.\s\w+\s20\d\d\s', re.UNICODE)
additives_regex = re.compile(r'\s\([A-Z0-9,\s]+\)\s?', re.UNICODE)


# Grabbed directly from itertools recipes
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx
    args = [iter(iterable)] * n
    return itt.izip_longest(fillvalue=fillvalue, *args)


def format_menu(date, dishes):
    """ Format a datetime and a list of dishes as a markdown message. """
    # https://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
    menu = u"# Lunch: {0:%A}".format(date)
    menu += u"\n\n## Piccante"
    for d in dishes:
        menu += u'\n* {}'.format(d)
    return menu


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Post today's lunch menu to Gitter.")
    parser.add_argument('hook', metavar='url', type=str,
                        help='The Gitter webhook URL.')
    args = parser.parse_args()
    # Get and parse html
    req = requests.get(menu_url)
    soup = bs4.BeautifulSoup(req.text, 'html.parser')
    # Find menu section
    menu_parent = soup.find(id='c822').find(class_="csc-textpic-text")
    # Remove cruft and join into one big string
    # Necessary because of messy html
    menu_string = ' '.join(itt.takewhile(
        lambda s: 'Die aktuelle Speisekarten' not in s,
        menu_parent.stripped_strings))
    # Extract day and dishes into dict
    days_dishes = grouper(day_regex.split(menu_string)[1:], 2)
    menu = {int(day): dishes for day, dishes in days_dishes}
    # Get today's dishes
    today = datetime.datetime.today()
    dishes_string = menu[today.day]
    # Separate using additives list
    dishes = additives_regex.split(dishes_string)[:-1]
    message = format_menu(today, dishes)
    # Post
    r = requests.post(args.hook, data={'message': message})
