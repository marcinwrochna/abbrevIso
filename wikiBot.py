#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
A bot for scraping Wikipedia infobox journals and fixing redirects from
ISO 4 abbreviations of journal titles.

Note [[Template:Infobox journals]] has synonims, see: 
	https://en.wikipedia.org/w/index.php?title=Special:WhatLinksHere/Template:Infobox_journal&hidetrans=1&hidelinks=1
"""
from __future__ import unicode_literals
import json
import logging
import os
import re
import sys
import time
from unicodedata import normalize

import pywikibot
from pywikibot import pagegenerators as pg
import pywikibot.data.api
import mwparserfromhell

"""`state` is a global variable maintained between runs.
	state = {
		'pages': {
			'Wiki Page Title': {
				'infoboxes': [{'title': 'IJ Title', 'issn': ..., 'abbreviation': ..., ...}, ...],
				'redirects': {'Redirect Page Title': 'Redirect Page Wikitext Content', ...},
			},
			...
		},
		'abbrevs': {
			'Wiki Page or Infobox Tile': {
				'eng': 'abbrevISO computed abbreviation using only eng,mul,lat,und LTWA rules',
				'all': 'using all rules'
			},
			...
		},
		'lastScrape': unix time of last finished scrape,
"""
state = {}
STATE_FILE_NAME = 'abbrevBotState.json';


def main():
	global site, state
	logging.basicConfig(level=logging.WARNING)
	loadOrInitState()
	# Initialize pywikibot.
	site = pywikibot.Site('en')
	# Run the given command or print a help message.
	if len(sys.argv) != 2:
		printHelp()
	elif sys.argv[1] == 'scrape':
		doScrape()
	elif sys.argv[1] == 'fixpages':
		doScrape(fixPages=True)
	elif sys.argv[1] == 'report':
		doReport()
	else:
		printHelp()
	saveState()


def printHelp():
	"""Prints a simple help message on available commands."""
	print("Use exactly one command of: scrape, fixpages, report")


def loadOrInitState():
	"""Load `state` from `STATE_FILE_NAME` or create a new one."""
	global state, STATE_FILE_NAME
	opened = False
	try:
		with open(STATE_FILE_NAME, 'rt') as f:
			opened = True
			state = json.load(f)
	except IOError:
		# If there's an error after opening, when reading, we don't catch the
		# exception but fail instead, so that the state file is not overwritten.
		if opened:
			raise
		else:
			print('Initiating empty bot state.')
			state = {'lastScrape': 0, 'pages': {}, 'abbrevs': {}}


def saveState():
	"""Save `state` to `STATE_FILE_NAME`."""
	global state, STATE_FILE_NAME
	with open(STATE_FILE_NAME, 'wt') as f:
		json.dump(state, f)


def doScrape(fixPages=False, countLimit=10000, changesLimit=1):
	"""Scrape all pages transcluding Infobox Journal, update `state` and
	fix redirects to pages if `fixPages` is given.
	"""
	global status, site, countChanges, limitChanges
	template = pywikibot.Page(site, 'Template:Infobox journal', ns=site.namespaces['Template']) #10
	gen = template.embeddedin(filter_redirects=False, namespaces=0, total=25000, content=True) # Omit redirects, mainspace only, limit total, immediately fetch content.
	t = time.time()
	countPages = 0
	countChanges = 0
	limitChanges = changesLimit
	for page in gen:
		countPages = countPages + 1
		print('--Scraping:\t', countPages, '\t', page.title(), end='\t', flush=True)
		scrapePage(page, t)
		print('', flush=True)
		if fixPages:
			fixPageRedirects(page)
		if countPages >= countLimit:
			return
	state['lastScrape'] = t

# Another way to write this is to use the following wrapper:
#gen = pg.ReferringPageGenerator(template, onlyTemplateInclusion=True) # This yields ~7500 pages.
# Alternatively we could iterate through categories, like this:
# cat = pywikibot.Category(site, 'Category:Articles with missing ISO 4 redirects') # Yields ~2000.
# cat = pywikibot.Category(site, 'Category:English-language_journals') # Yields ~6000.
# cat = pywikibot.Category(site, 'Category:Academic journals') # Yields ????
# In the last case you'd probably want to exclude the subcat 'Literary magazines'
# (in 'Humanities journals') which includes all kinds of comic book magazines, for example.
# for page in cat.articles(recurse = True, namespaces = 0, pages = 15000) # recurse = n limits depth, pages limits total yield, content=True?
# or
# gen = pagegenerators.CategorizedPageGenerator(cat, recurse = True, total = 15000, namespaces = 0)	


def fixPageRedirects(page, simulateOnly=True):
	global state, site, countChanges, limitChanges
	title = page.title()
	pageData = state['pages'][title]
	rNewContent = '#REDIRECT [[' + title + ']]\n{{R from ISO 4}}'
	requiredRedirects = {}
	for infobox in pageData['infoboxes']:
		if 'title' in infobox:
			name = infobox['title']
		else:
			name = title
		if 'abbreviation' not in infobox:
			continue
		iabbrev = infobox['abbreviation']
		iabbrevDotless = iabbrev.replace('.', '')
		# If a valid ISO 4 redirect already exists for dotted version,
		# create (or attempt replacing) one for the dotless version too.
		if iabbrev in pageData['redirects'] \
				and isValidISO4Redirect(pageData['redirects'][iabbrev], title):
			requiredRedirects[iabbrevDotless] = rNewContent;
			continue
		# If the abbreviation matches the computed one, create (or
		# attempt replacing) both redirects.
		# The soft match might not be exact (eg. cutting subtitles). We
		# use the (human-edited) abbreviation from the infobox parameter. 
		if name not in state['abbrevs'] or not state['abbrevs'][name]:
			print('No computed abbreviation stored for "' + name + '".')
			continue
		cabbrev = state['abbrevs'][name][getLanguage(infobox)]
		if not isSoftMatch(iabbrev, cabbrev):
			print('--Abbreviations don\'t match, ignoring [[' + title + ']].')
			continue
		requiredRedirects[iabbrev] = rNewContent;
		requiredRedirects[iabbrev.replace('.', '')] = rNewContent;
	for rTitle, rNewContent in requiredRedirects.items():
		if rTitle not in pageData['redirects']:
			if pywikibot.Page(site, rTitle).exists():
				print('--Skipping existing page [[' + rTitle + ']] (not a redirect to [[' + title + ']]).')
				continue
			print('--Creating redirect from [[' + rTitle + ']] to [[' + title + ']]. Created content:\n')
			print(rNewContent)
			print('\n-----')
			if not simulateOnly:
				countChanges = countChanges + 1
				if countChanges > limitChanges:
					continue
				rPage = pywikibot.Page(site, rTitle)
				rPage.text = rNewContent
				rPage.save(u'Creating redirect from ISO 4 abbreviation. '
					+ u'Report bugs and suggestions to [[User talk:TokenzeroBot]]',
					botflag=True,
					createonly=True)
		else:
			rOldContent = pageData['redirects'][rTitle]
			if isValidISO4Redirect(rOldContent, title):
				print('--Skipping existing valid redirect from [[' + rTitle + ']] to [[' + title + ']].')
				pass
			elif isReplaceableRedirect(rOldContent, title, rTitle):
				print('--Replacing existing redirect from [[' + rTitle + ']] to [[' + title + ']]. Original content:\n')
				print(rOldContent)
				print('\n----- New content:\n')
				print(rNewContent)
				print('\n-----')
				if not simulateOnly:
					countChanges = countChanges + 1
					if countChanges > limitChanges:
						continue
					rPage = pywikibot.Page(site, rTitle)
					rPage.text = rNewContent
					rPage.save(u'Marking as {{R from ISO 4}}. '
						+ u'Report bugs and suggestions to [[User talk:TokenzeroBot]]',
						botflag=True,
						nocreate=True)
			else:
				print('--Skipping existing dubious redirect from [[' + rTitle + ']] to [[' + title + ']].')
				#print(rOldContent)
				#print('\n-----')


def doReport():
	global state
	#print(json.dumps(state, indent = "\t"))
	#printReportOnInfoboxPerPageNumbers()
	# Numbers of infobox-journals:
	nIJsWithoutAbbrev = 0; # With no (human) abbreviation parameter.
	nIJsWithMissingAbbrev = 0; # With no computed abbreviation.
	nIJsWithExactMatch = 0; # With exact match.
	nIJsWithCompatMatch = 0; # With match up to e.g. removing parens.
	nIJsWithMismatch = 0; # With mismatch.
	for title, page in state['pages'].items():
		for infobox in page['infoboxes']:
			name = infobox.get('title', title)
			if 'abbreviation' not in infobox or infobox['abbreviation'] == '':
				nIJsWithoutAbbrev += 1
			elif name not in state['abbrevs']:
				nIJsWithMissingAbbrev += 1
			else:
				iabbrev = infobox['abbreviation']
				cabbrev = state['abbrevs'][name][getLanguage(infobox)]
				cabbrev = normalize('NFC', cabbrev).strip()
				if iabbrev == cabbrev:
					nIJsWithExactMatch += 1
				elif isSoftMatch(iabbrev, cabbrev):
					nIJsWithCompatMatch += 1
				else:
					nIJsWithMismatch += 1
	print(nIJsWithoutAbbrev, nIJsWithMissingAbbrev, nIJsWithExactMatch, nIJsWithCompatMatch, nIJsWithMismatch)
	
	#for title, page in sorted(state['pages'].items()):
	#	doTry(title, page)


def printReportOnInfoboxPerPageNumbers():
	global state
	print("==Number of infoboxes per page==")
	result = {}
	for title, page in state['pages'].items():
		l = len(page['infoboxes'])
		if (l not in result):
			result[l] = []
		result[l].append(title)
	for i in result:
		print("There are", len(result[i]), "pages with", i, "infoboxes.")
		if i == 0 or i >= 5:
			for title in result[i]:
				print("[[", title, "]]")


def printReportOnUnexpectedISO4Redirects():
	"""Print a report on existing redirects tagged as ISO 4 that might
	be wrong (the bot would not add them).
	
	There are valid cases for such redirects:
	* from former names (inc. mergers): Mycol. Bull., Queen's Intramural Law J.
	* from other language title: Rev. Can. Santé Publique
	* from alternative (arguably equally good) capitalization: PLoS Comput. Biol., PLoS Genet. 
	Abbreviated single word titles are the most common error.
	"""
	for rTitle, rContent in page['redirects'].items():
		if not re.search(r'R from ISO 4', rContent):
			continue
		if not rTitle not in requiredRedirects:
			continue
		# Ignore rTitle that contain a computed abbreviation as a
		# substring, assume that it's some valid variation on a subtitle.
		good = True
		for computedAbbrev in requiredRedirects.keys():
			if re.sub(r'\s*[:(].*', '', computedAbbrev) in rTitle:
				good = False
				break
		if not good:
			continue
		print('The following redirect might be wrongly marked as "R from ISO 4": [[' + rTitle + ']] -> [[' + title + ']],', list(requiredRedirects.keys())[0] ,'currently:')
		print(rContent)


def getLanguage(infobox):
	"""Guess the language of an IJ's title.
	
	Returns 'eng' or 'all'. This affects which LTWA rules we use when 
	selecting the abbrevISO computed abbreviation.
	We assume the title is English if the country is anglophone and the
	language parameter does not specify sth else. Note there are
	non-English titles with the language infobox parameter set to
	English, because they publish in English only.
	"""
	englishCountries = ['United States', 'U.S.', 'U. S.', 'USA', 'U.S.A', 'US', 'United Kingdom', 'UK', 'New Zealand', 'Australia', 'UK & USA', 'England']
	l = infobox.get('language', '')
	if not l.strip() or l.startswith('English'):
		if infobox.get('country', '') in englishCountries:
			return 'eng'
	return 'all'


def isSoftMatch(infoboxAbbrev, computedAbbrev):
	"""Return whether an abbreviation can be considered correct according to the computed one.
	
	For this we ignore comments from the infobox abbreviation
	and ignore dependent titles from the computed abbreviation.
	"""
	if infoboxAbbrev == computedAbbrev:
		return True
	if re.sub(r'\s*\(.*', '', infoboxAbbrev) == re.sub(r'\s*:.*', '', computedAbbrev):
		return True
	return False


def isValidISO4Redirect(rContent, title):
	"""Return whether the content of a given redirect page is already
	just a simple variation of what we would put.
	"""
	# Normalize special characters.
	rContent = rContent.replace('&#38;', '&')
	rContent = rContent.replace('&#39;', '\'')
	rContent = rContent.replace('_', ' ')
	# Normalize whitespace.
	rContent = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', rContent.strip())
	title = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', title.strip())
	# Normalize capitalization.
	rContent = rContent.replace('redirect', 'REDIRECT')
	rContent = rContent.replace('Redirect', 'REDIRECT')
	# Ignore `(un)printworthy` rcats.
	rContent = re.sub(r'{{R(EDIRECT)? (un)?printworthy}}', '', rContent)
	rContent = re.sub(r'{{R(EDIRECT)? u?pw?}}', '', rContent)
	# Ignore variants including the rcat shell.
	rContent = rContent.replace('{{REDIRECT category shell', '{{REDIRECT shell')
	rWithoutShell = '#REDIRECT[[' + title + ']]{{R from ISO 4}}'
	rWithShell = '#REDIRECT[[' + title + ']]{{REDIRECT shell|{{R from ISO 4}}}}'
	return rContent == rWithoutShell or rContent == rWithShell

def isReplaceableRedirect(rContent, title, rTitle):
	"""Return whether the content of a given redirect page can be
	automatically replaced.
	
	Examples of not replaceable content:
		redirects to specific article sections, to disambuigs,
		unexpected rcats or rcats with some parameters filled,
		rcat "from move".
	"""
	# Normalize special characters.
	rContent = rContent.replace('&#38;', '&')
	rContent = rContent.replace('&#39;', '\'')
	rContent = rContent.replace('_', ' ')
	# Normalize whitespace.
	rContent = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', rContent.strip())
	title = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', title.strip())
	# Normalize capitalization.
	rContent = rContent.replace('redirect', 'REDIRECT')
	rContent = rContent.replace('Redirect', 'REDIRECT')
	# Allow removing `(un)printworthy` rcats.
	rContent = re.sub(r'{{R(EDIRECT)? (un)?printworthy}}', '', rContent)
	rContent = re.sub(r'{{R(EDIRECT)? u?pw?}}', '', rContent)
	# Allow removing at most one other abbreviation or spelling rcat.
	# E.g. don't change pages having an {{R from move}}.
	#rContent = re.sub(r'{{R from[a-zA-Z4\s]*}}', '', rContent, 1)
	rContent = re.sub(r'{{R from (ISO 4|abb[a-z]*|shortening|initialism|short name|alternat[a-z]* spelling|systematic abbreviation|other capitalisation|other spelling)}}', '', rContent, 1)
	# Report redirects describing dotless ISO 4 in a certain specific way.
	#rContent = re.sub(r'{{R from modification[|]\'\'{{-r[|][a-zA-Z0-9\-\.\s]*}}\'\'}}', '', rContent, 1)
	if rContent != re.sub(r'{{R from modification[|]\'\'{{-r[|][a-zA-Z0-9\-\.\s]*}}\'\'}}', '', rContent, 1):
		print('{{noredirect|' + rTitle + '}}')
	# Allow removing a common bug (an rcat without '{{}}').
	rContent = re.sub(r'R from abbreviation', '', rContent, 1)
	# Allow removing/adding the rcat shell.
	rContent = re.sub(r'{{REDIRECT shell\s*[|](1=)?\s*}}', '', rContent)
	rContent = re.sub(r'{{REDIRECT category shell\s*[|](1=)?\s*}}', '', rContent)
	return rContent == '#REDIRECT[[' + title + ']]'


def getGeneratorOfRedirectsToPage(pageTitle, namespaces=None, total=None, content=False):
	"""Iterate over pages that are redirects to `page`.

	Note that page.backlinks(filterRedirects=True) should not be used!
	It also returns pages that include a link to `page` and happend to 
	be redirects to a different, unrelated page (e.g. every redirect
	from a Bluebook abbrev includes a [[Bluebook]] link).
		for r in page.backlinks(followRedirects=False, filterRedirects=True, namespaces=0, total=100, content=True):
	Note also we disregard double redirects: these are few and
	eventually resolved by dedicated bots.
	"""
	return site._generator(pywikibot.data.api.PageGenerator,
		type_arg="redirects",
		titles=pageTitle,
		grdprop="pageid|title|fragment",
		namespaces=namespaces,
		total=total,
		g_content=content)


def scrapePage(page, time):
	"""Scrape a page's infoboxes and redirects."""
	global state, site
	pageData = {'infoboxes': [], 'redirects': {}, 'lastScraped': time}
	# We could use the pywikibot interface to it, but it may fall-back to regex,
	# reorder parameters, and mwparserfromhell is better documented.
	#   p = pywikibot.textlib.extract_templates_and_params(page.text)
	#   text = pywikibot.textlib.glue_template_and_params(p)
	p = mwparserfromhell.parse(normalize('NFC', page.text))
	# Iterate over {{infobox journal}} template instances on `page`.
	for t in p.filter_templates():
		if t.name.matches('infobox journal') or t.name.matches('Infobox Journal'): #mwpfh only normalizes the first letter.
			print('I', end='', flush=True)
			infoboxData = {}
			for param in t.params:
				if param.name.lower().strip() in ['title', 'issn', 'abbreviation', 'language', 'country', 'former_name', 'bluebook']:
					infoboxData[str(param.name).lower().strip()] = str(param.value).strip()
			pageData['infoboxes'].append(infoboxData)
			if 'title' in infoboxData and infoboxData['title'] != '':
					if infoboxData['title'] not in state['abbrevs']:
						state['abbrevs'][infoboxData['title']] = False
	# Iterate over pages that are redirects to `page`.
	for r in getGeneratorOfRedirectsToPage(page.title(), namespaces=0, total=100, content=True):
		print('R', end='', flush=True) #r.getRedirectTarget().title()
		pageData['redirects'][r.title()] = r.text

	state['pages'][page.title()] = pageData
	# Remove disambuigation comments from wiki title before computing abbreviation.
	title = re.sub(r'\s*\(.*(ournal|agazine|eriodical|eview)s?\)', '', page.title())
	if title not in state['abbrevs']:
		state['abbrevs'][title] = False


if __name__ == "__main__":
	main()

