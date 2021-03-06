#! /usr/bin/env python
"""
Converts a given parameter in a template to use {{start date}}
$ python startdate.py name_of_infobox_to_convert name_of_param_to_convert
"""

from __future__ import unicode_literals

import mwclient
import mwparserfromhell

import sys
import re

from theobot import bot
from theobot import password

from datetime import datetime
import dateutil.parser as parser

# CC-BY-SA Theopolisme

# Monkey-patch the `parse` method
# This sets None as the default value for missing parameters and raises a ValueError for ambiguous dates
def parse(self,timestr,default=None,ignoretz=False,tzinfos=None,**kwargs):
	# _result() objects are unique, so we convert to unicode to compare them 
	if unicode(self._parse(timestr, **kwargs)) == unicode(self._parse(timestr, yearfirst=True, **kwargs)) == unicode(self._parse(timestr, dayfirst=True, **kwargs)):
		return self._parse(timestr, **kwargs)
	else:
		raise ValueError("The date was ambiguous: %s" % timestr)
parser.parser.parse = parse

def process(page):
	contents = page.edit()
	wikicode = mwparserfromhell.parse(contents)
	for template in wikicode.filter_templates():
		if template.name.lower().strip() in INFOBOX_TITLES and template.has_param(PARAM):
			pub_date_stripped = template.get(PARAM).value.strip_code().strip() # This helps with parsing wikicode-ified dates
			pub_date_raw = template.get(PARAM).value.strip()
			if pub_date_raw.lower().find("{{start") == -1 and pub_date_raw.find("[[Category:Infoboxes needing manual conversion") == -1:
				try:
					date = parser.parser().parse(pub_date_stripped,None)
				except ValueError:
					# If the date is ambiguous, e.g., "2-2-2012," tag it for manual conversion
					date = None

				if date is None or date.year is None:
					if pub_date_raw.find("<!-- Date published") == -1:
						template.add(PARAM,pub_date_raw+" [[Category:Infoboxes needing manual conversion to use start date]]")
						page.save(unicode(wikicode),u'[[WP:BOT|Bot]]: Tagging unparsable {}'.format(PARAM))
						continue
					else:
						continue					

				if date.utcoffset() and date.utcoffset().total_seconds() != 0:
					# If the date has timezone info and the timezone isn't UTC, skip it 
					template.add(PARAM,pub_date_raw+" [[Category:Infoboxes needing manual timezone conversion to use start date]]")
					page.save(unicode(wikicode),u'[[WP:BOT|Bot]]: Tagging {} in need of manual conversion to use [[Template:Start date]]'.format(PARAM))
					continue

				if not (1583 <= date.year <= 9999): # {{start date}} is only for dates in the ISO 8601 date range
					template.add(PARAM,pub_date_raw+" <!-- Date should NOT be converted to use {{start date}}, since it is outside of the ISO 8601 date range -->")
					page.save(unicode(wikicode),u'[[WP:BOT|Bot]]: Tagging out-of-range {}'.format(PARAM))
					continue

				if re.search(r"""\d{1,2} [a-zA-Z]* \d{4}""",pub_date_raw,flags=re.U) is not None:
					df = True
				else:
					df = False
				startdate = mwparserfromhell.nodes.Template(name='start date')
				if date.year:
					startdate.add(1,date.year)
				if date.month:
					startdate.add(2,date.month)
				if date.day:
					startdate.add(3,date.day)				
				if date.hour:
					startdate.add(4,date.hour)
				if date.minute:
					startdate.add(5,date.minute)
				if date.second:
					startdate.add(6,date.second)
				if df:
					startdate.add('df','y')
				template.add(PARAM,unicode(startdate)+"<!-- Bot-converted date -->")
				page.save(unicode(wikicode),u'[[WP:BOT|Bot]]: Converting '+PARAM+' to utilize {{[[Template:start date|]]}}')
			else:
				continue

def main():
	global site
	site = mwclient.Site('en.wikipedia.org')
	site.login(password.username, password.password)

	print "Logged in to site; getting template details."
	global INFOBOX,PARAM,INFOBOX_TITLES
	INFOBOX = sys.argv[1].replace('_',' ')
	PARAM = sys.argv[2]
	INFOBOX_TITLES = [title.strip().lower() for title in bot.redirects(INFOBOX,namespace=10,pg_prefix="Template:",output='page_title')]
	INFOBOX_TITLES += INFOBOX

	print "Getting transclusions..."
	for page in bot.what_transcludes(INFOBOX):
		page = site.Pages[page['title']]
		process(page)

if __name__ == '__main__':
	main()
