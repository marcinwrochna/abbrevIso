#!/usr/bin/python3
import sys
import logging
logging.basicConfig(level=logging.WARNING)

import mwparserfromhell

import mwclient
site = mwclient.Site('en.wikipedia.org', clients_useragent='LTWAsearch/0.1 (User:Tokenzero, mwrochna@gmail.com)  mwclient', max_lag=2)
count = 0

args = ['title', 'issn', 'abbreviation', 'language', 'country', 'former_name', 'bluebook', 'discipline', 'peer-reviewed', 'publisher', 'history', 'openaccess', 'license', 'impact', 'impact-year', 'CODEN', 'JSTOR', 'LCCN', 'OCLC', 'ISSNlabel', 'eISSN']

head = []
head.append('name')
head.append('infoboxid')
for arg in args:
	head.append(arg)
head.append('category')
print('#' + ('\t'.join(head)))


def transclusions(site, name, namespace='0', filterredir='all', limit=None, generator=True):
	return mwclient.listing.PageList(site, namespace=10)[name].embeddedin(namespace=namespace, filterredir=filterredir, generator=generator)

def listJournals(category):
	if category.name== 'Category:Literary magazines': # Category:Humanities journals includes Category:Literary magazines which includes all kinds of comic book magazines, for example.
		return
	for page in category:
		if page.namespace == 14:
			listJournals(page)
		elif page.namespace == 0:
			parsePage(page, category.name)
			
def parsePage(page, categoryName = 'NULL'):
		p = mwparserfromhell.parse(page.text())
		localcount = 0
		for t in p.filter_templates():
			if t.name.lower().strip() == 'infobox journal':
				localcount = localcount + 1
				global count
				count = count + 1	
				#if count > 5:
				#	sys.exit()
				result = []
				result.append(page.name.strip())
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
			
#listJournals(site.Categories['English-language_journals']) #~6000
#listJournals(site.Categories['Academic_journals']) #~???? aborted at 15478 with Literary magazines.

for page in transclusions(site, 'infobox journal'): #~7378
	parsePage(page)
