#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import mwparserfromhell
import pywikibot
from pywikibot import pagegenerators as pg
import re
import sys


logging.basicConfig(level=logging.WARNING)

#import mwclient
#site = mwclient.Site('en.wikipedia.org', clients_useragent='LTWAsearch/0.1 (User:Tokenzero, mwrochna@gmail.com)  mwclient', max_lag=2)
count = 0

args = ['title', 'issn', 'abbreviation', 'language', 'country', 'former_name', 'bluebook', 'discipline', 'peer-reviewed', 'publisher', 'history', 'openaccess', 'license', 'impact', 'impact-year', 'CODEN', 'JSTOR', 'LCCN', 'OCLC', 'ISSNlabel', 'eISSN']

head = []
head.append('name')
head.append('infoboxid')
for arg in args:
	head.append(arg)
head.append('category')
print('#' + ('\t'.join(head)))


# In mwclient
#def transclusions(site, name, namespace='0', filterredir='all', limit=None, generator=True):
#	return mwclient.listing.PageList(site, namespace=10)[name].embeddedin(namespace=namespace, filterredir=filterredir, generator=generator)

# def listJournals(category):
# 	# TODO do no reenter categories.
# 	if category.name == 'Category:Literary magazines': # Category:Humanities journals includes Category:Literary magazines which includes all kinds of comic book magazines, for example.
# 		return
# 	for page in category:
# 		if page.namespace == 14:
# 			listJournals(page)
# 		elif page.namespace == 0:
# 			parsePage(page, category.name)

def parsePage(page, categoryName = 'NULL'):
		#page.backlinks(followRedirects=True,filterRedirects=True,namespaces=0,total=100,content=True)
		p = mwparserfromhell.parse(page.text)
		# You could use the pywikibot interface to it, but it may fall-back to regex,
		# reorder parameters, and mwparserfromhell is better documented.
		#   p = pywikibot.textlib.extract_templates_and_params(page.text)
		#   text = pywikibot.textlib.glue_template_and_params(p)
		localcount = 0
		for t in p.filter_templates():
			if t.name.lower().strip() == 'infobox journal':
				localcount = localcount + 1
				global count
				count = count + 1
				if count > 5:
					sys.exit()
				result = []
				result.append(page.title().strip())
				result.append(str(localcount))
				for arg in args:
					if (t.has(arg)):
						s = str(t.get(arg).value.strip_code())
						s = s.replace('\t', ' ')
						s = '    '.join(s.splitlines())
						result.append(s.strip())
					else:
						result.append('NULL')
				result.append(categoryName)
				print('\t'.join(result))
		if localcount == 0:
			result = []
			result.append(page.name.strip())
			for arg in args:
					result.append('NULL')
			result.append(categoryName)
			print('\t'.join(result))

site = pywikibot.Site('en')

# Note Template:Infobox journals has synonims, see: https://en.wikipedia.org/w/index.php?title=Special:WhatLinksHere/Template:Infobox_journal&hidetrans=1&hidelinks=1
template = pywikibot.Page(site, 'Template:Infobox journal', ns=10) #site.NamespacesDict('Template')
# gen = template.embeddedin(filterRedirects = False, namespaces = 0, total = 25000, content= True) // Omit redirects, mainspace only, limit total, immediately fetch content.
gen = pg.ReferringPageGenerator(template, onlyTemplateInclusion=True) # This yields ~7500 pages.
# Alternatively we could iterate through categories, like this:
# cat = pywikibot.Category(site, 'Category:Articles with missing ISO 4 redirects') # Yields ~2000.
# cat = pywikibot.Category(site, 'Category:English-language_journals') # Yields ~6000.
# cat = pywikibot.Category(site, 'Category:Academic journals') # Yields ????
# In the last case you'd probably want to exclude the subcat 'Literary magazines'
# (in 'Humanities journals') which includes all kinds of comic book magazines, for example.
#for page in cat.articles(recurse = True, namespaces = 0, pages = 15000) # recurse = n limits depth, pages limits total yield, content=True?
# or
#gen = pagegenerators.CategorizedPageGenerator(cat, recurse = True, total = 15000, namespaces = 0)

for page in gen:
	parsePage(page)
