#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
A bot for scraping Wikipedia infobox journals and fixing redirects from
ISO 4 abbreviations of journal titles.
"""
from __future__ import unicode_literals
import logging
import re
import sys
from unicodedata import normalize
import Levenshtein

import pywikibot
import pywikibot.data.api
import mwparserfromhell

import utils, report, state


# Some basic config
scrapeLimit = 10000  # Max number of pages to scrape.
totalEditLimit = 20  # Max number of edits to make (in one run of the script).
onlySimulateEdits = False  # If true, only print what we would do, don't edit.
STATE_FILE_NAME = 'abbrevBotState.json'

site = None # pywikibot's main object.

def main():
    global site, onlySimulateEdits
    logging.basicConfig(level=logging.WARNING)
    state.loadOrInitState(STATE_FILE_NAME)
    # Initialize pywikibot.
    site = pywikibot.Site('en')
    # Run the given command or print a help message.
    if len(sys.argv) != 2:
        printHelp()
    elif sys.argv[1] == 'test':
        doTest()
    elif sys.argv[1] == 'scrape':
        doScrape()
    elif sys.argv[1] == 'report':
        onlySimulateEdits = True
        doScrape(fixPages=True, writeReport=True)
    elif sys.argv[1] == 'fixpages':
        doScrape(fixPages=True, writeReport=True)
    elif sys.argv[1] == 'fill':
        doFillAbbrevs()
    else:
        printHelp()
    state.saveState(STATE_FILE_NAME)


def printHelp():
    """Prints a simple help message on available commands."""
    print("Use exactly one command of: scrape, fixpages, report, test")


def doTest():
    """Test a bot edit (in userspace sandbox), e.g. to check flags."""
    global site
    # print(state.dump())
    page = pywikibot.Page(site, u"User:TokenzeroBot/sandbox")
    page.text = 'Testing bot.'
    page.save(
        u'Testing bot',
        minor=False,
        botflag=True,
        watch="nochange",
        nocreate=True)


def doFillAbbrevs():
    """Fill empty abbreviations in some automatizable cases.

    Currently the cases are:
    * abbreviation is equal to title, possibly without articles (a/the)
    """
    global site
    cat = 'Category:Infobox journals with missing ISO 4 abbreviations'
    cat = pywikibot.Category(site, cat)
    nScraped = 0  # Number of scraped pages (excluding redirects).
    nEdited = 0  # Number of edits (including on redirects).
    for page in cat.articles(namespaces=0, total=scrapeLimit, content=True):
        print('--Scraping:\t', nScraped, '\t')
        print(page.title(), flush=True)
        i = 0
        for infobox in getInfoboxJournals(page):
            if infobox.get('abbreviation', '') != '':
                print('--Skipping infobox that actually has non-empty abbrev')
                continue;
            title = stripTitle(page.title())
            if 'title' in infobox and infobox['title'] != title:
                print('--Skipping infobox with different title than article', infobox['title'])
                continue
            try:
                cLang = utils.getLanguage(infobox)
                cAbbrev = state.getAbbrev(title, cLang)
            except state.NotComputedYetError:
                print('No computed abbreviation stored for',
                      '"' + title + '"',
                      ', please rerun abbrevIsoBot.js .')
                state.saveTitleToAbbrev(stripTitle(page.title()))
                continue
            # If abbreviation is equal to title, up to "a/the" articles:
            if cAbbrev == re.sub(r'(The|the|A|a)\s+', '', title):
                print('--Filling "'+ title +'" with abbrev "' + cAbbrev +'"')
                page.text = fillAbbreviation(page.text, i, cAbbrev)
                if not onlySimulateEdits:
                    try:
                        page.save(
                            u'Filling trivial ISO-4 abbreviation. '
                                + u'Report bugs and suggestions '
                                + u'to [[User talk:TokenzeroBot]]',
                            minor=True,
                            botflag=True)
                        print('--save modify OK---------------------------')
                    except pywikibot.PageNotSaved:
                        print('--SAVE MODIFY FAILED-----------------------')
                    nEdited = nEdited + 1
                    if nEdited >= totalEditLimit:
                        return
            i = i + 1
    nScraped = nScraped + 1
    if nScraped >= scrapeLimit:
        return


def fillAbbreviation(pageText, whichInfobox, abbrev):
    """Return pageText with changed abbreviation in specified infobox."""
    p = mwparserfromhell.parse(pageText)
    i = 0
    for t in p.filter_templates():
        if t.name.matches('infobox journal') or \
           t.name.matches('Infobox Journal'):
            if i == whichInfobox:
                if t.has_param('title') and t.get('title')[0] == ' ':
                    abbrev = ' ' + abbrev
                t.add('abbreviation', abbrev, preserve_spacing=True)
            i = i + 1
    return str(p)


def doScrape(fixPages=False, writeReport=False):
    """Scrape all pages transcluding Infobox Journal, update `state` and
    fix redirects to pages if `fixPages` is True.
    """
    global site
    gen = getPagesWithInfoboxJournals(scrapeLimit)
    nScraped = 0  # Number of scraped pages (excluding redirects).
    nEdited = 0  # Number of edits (including on redirects).
    for page in gen:
        print('--Scraping:\t', nScraped, '\t')
        print(page.title(), end='\t', flush=True)
        scrapePage(page)
        if fixPages:
            r = fixPageRedirects(
                page,
                editLimit=totalEditLimit - nEdited,
                simulateOnly=onlySimulateEdits)
            nEdited += r
            if nEdited >= totalEditLimit:
                break
        nScraped = nScraped + 1
        if nScraped >= scrapeLimit:
            break
    if writeReport:
        report.doReport(site)


def stripTitle(t):
    """Remove disambuig comments from wiki title (before computing abbreviation).
    """
    t = re.sub(r'\s*\(.*(ournal|agazine|eriodical|eview)s?\)', '', t)
    return t


def scrapePage(page):
    """Scrape a page's infoboxes and redirects, save them in the `state`.
    """
    global site
    pageData = {'infoboxes': [], 'redirects': {}}
    # Iterate over {{infobox journal}}s on `page`.
    for infobox in getInfoboxJournals(page):
        print('I', end='', flush=True)
        pageData['infoboxes'].append(infobox)
        if 'title' in infobox and infobox['title'] != '':
            state.saveTitleToAbbrev(infobox['title'])
    # Iterate over pages that are redirects to `page`.
    for r in getRedirectsToPage(page.title(), namespaces=0,
                                total=100, content=True):
        print('R', end='', flush=True)
        pageData['redirects'][r.title()] = r.text
        # r.getRedirectTarget().title()
    state.savePageData(page.title(), pageData)
    state.saveTitleToAbbrev(stripTitle(page.title()))
    print('', flush=True)


def fixPageRedirects(page, editLimit=10, simulateOnly=True):
    """Fix redirects to given page (but at most `editLimit`).

    If `simulateOnly` is true, we only print what we would do.
    """
    global site
    title = page.title()
    pageData = state.getPageData(title)
    rNewContent = '#REDIRECT [[' + title + ']]\n{{R from ISO 4}}'
    requiredRedirects, skip = getRequiredRedirects(page)
    nEditedPages = 0
    for (rTitle, (rNewContent, iTitle)) in requiredRedirects.items():
        # Attempt to create new redirect.
        if rTitle not in pageData['redirects']:
            if pywikibot.Page(site, rTitle).exists():
                print('--Skipping existing page [[' + rTitle + ']] '
                      + '(not a redirect to [[' + title + ']]).')
                report.reportExistingOtherPage(title, iTitle, rTitle)
                continue
            print('--Creating redirect '
                  + 'from [[' + rTitle + ']] to [[' + title + ']]. '
                  + 'Created content:\n' + rNewContent + '\n-----',
                  flush=True)
            if nEditedPages >= editLimit:
                return nEditedPages
            nEditedPages = nEditedPages + 1
            if not simulateOnly:
                rPage = pywikibot.Page(site, rTitle)
                rPage.text = rNewContent
                try:
                    rPage.save(
                        u'Creating redirect from ISO 4 abbreviation. '
                        + u'Report bugs and suggestions '
                        + u' to [[User talk:TokenzeroBot]]',
                        minor=False,
                        botflag=True,
                        watch="nochange",
                        createonly=True)
                    print('--save create OK---------------------------')
                except pywikibot.PageNotSaved:
                    print('--SAVE CREATE FAILED-----------------------')
        else:
            rOldContent = pageData['redirects'][rTitle]
            if isValidISO4Redirect(rOldContent, title):
                print('--Skipping existing valid redirect '
                      + 'from [[' + rTitle + ']] to [[' + title + ']].')
            elif isReplaceableRedirect(rOldContent, title, rTitle):
                print('--Replacing existing redirect '
                      + 'from [[' + rTitle + ']] to [[' + title + ']]. '
                      + 'Original content:\n' + rOldContent + '\n----- '
                      + 'New content:\n' + rNewContent + '\n-----', flush=True)
                if nEditedPages >= editLimit:
                    return nEditedPages
                nEditedPages = nEditedPages + 1
                if not simulateOnly:
                    rPage = pywikibot.Page(site, rTitle)
                    rPage.text = rNewContent
                    try:
                        rPage.save(
                            u'Marking as {{R from ISO 4}}. '
                            + u'Report bugs and suggestions '
                            + u'to [[User talk:TokenzeroBot]]',
                            minor=False,
                            botflag=True,
                            watch="nochange",
                            nocreate=True)
                        print('--save modify OK---------------------------')
                    except pywikibot.PageNotSaved:
                        print('--SAVE MODIFY FAILED-----------------------')
            else:
                print('--Skipping existing dubious redirect '
                      + 'from [[' + rTitle + ']] to [[' + title + ']].')
                report.reportExistingOtherRedirect(
                    title, iTitle, rTitle, rOldContent)
    if nEditedPages > 0:
        page.purge()
    # Report redirects that we wouldn't add, but exist and are marked as ISO-4.
    if requiredRedirects and not skip:
        for rTitle, rContent in pageData['redirects'].items():
            if not re.search(r'R from ISO 4', rContent):
                continue
            # Ignore rTitle that contain a computed abbreviation as a
            # substring, assume that it's some valid variation on a subtitle.
            isExpected = False
            for computedAbbrev in requiredRedirects.keys():
                if re.sub(r'\s*[:(].*', '', computedAbbrev) in rTitle:
                    isExpected = True
                    break
            if not isExpected:
                # Find closest computed abbrev.
                bestAbbrev = ''
                bestDist = len(rTitle)
                for computedAbbrev in sorted(list(requiredRedirects.keys())):
                    dist = Levenshtein.distance(rTitle, computedAbbrev)
                    if (dist < bestDist):
                        bestDist = dist
                        bestAbbrev = computedAbbrev
                # Skip if closest abbrev. is far (assume it's from a former
                # title, since there's a ton of cases like that).
                if bestDist <= 8:
                    report.reportSuperfluousRedirect(
                        title, rTitle, rContent, bestAbbrev)
    return nEditedPages


def getRequiredRedirects(page):
    """Compute ISO-4 redirects to `page` that we believe should exist.

    Returns `[req, skip]`, where:
        `req[redirectTitle] = [redirectContent, infoboxUnabbreviatedTitle]`,
        `skip` indicates that we had to skip an infobox, so the result is most
        probably not exhaustive (so we won't report extra existing redirects).
    """
    global site
    title = page.title()
    pageData = state.getPageData(title)
    rNewContent = '#REDIRECT [[' + title + ']]\n{{R from ISO 4}}'
    result = {}
    skip = False
    for infobox in pageData['infoboxes']:
        iTitle = infobox.get('title', '')
        if iTitle:
            name = iTitle
        else:
            name = stripTitle(title)
        iAbbrev = infobox.get('abbreviation', '')
        iAbbrevDotless = iAbbrev.replace('.', '')
        if iAbbrev == '' or iAbbrev == 'no':
            print('--Abbreviation param empty or "no", ignoring [[' + title + ']].')
            skip = True
            continue
        if ':' in iAbbrev[:5]:
            print('--Abbreviation contains early colon, ignoring [[' + title + ']].')
            report.reportTitleWithColon(
                title, infobox.get('title', ''), iAbbrev)
            skip = True
            continue
        # If a valid ISO 4 redirect already exists for dotted version,
        # there should be one for the dotless version too.
        hasISO4Redirect = False
        if iAbbrev in pageData['redirects'] \
                and isValidISO4Redirect(pageData['redirects'][iAbbrev], title)\
                and iAbbrevDotless != iAbbrev:
            result[iAbbrev] = (pageData['redirects'][iAbbrev], iTitle)
            result[iAbbrevDotless] = (rNewContent, iTitle)
            hasISO4Redirect = True
        # If the abbreviation matches the computed one,
        # there should be a dotted and a dotless redirect.
        try:
            cLang = utils.getLanguage(infobox)
            cAbbrev = state.getAbbrev(name, cLang)
        except state.NotComputedYetError:
            print('No computed abbreviation stored for "' + name + '", '
                  + 'please rerun abbrevIsoBot.js .')
            skip = True
            continue
        if not utils.isSoftMatch(iAbbrev, cAbbrev):
            print('--Abbreviations don\'t match, ignoring [[' + title + ']].')
            otherAbbrevs = state.getAllAbbrevs(name).values()
            otherAbbrevs = [a for a in otherAbbrevs
                            if utils.isSoftMatch(iAbbrev, a)]
            if otherAbbrevs:
                report.reportLanguageMismatch(
                    title, infobox.get('title', ''),
                    iAbbrev, cAbbrev, otherAbbrevs[0],
                    infobox.get('language', ''), infobox.get('country', ''),
                    cLang, state.getMatchingPatterns(name), hasISO4Redirect)
            else:
                report.reportProperMismatch(
                    title, infobox.get('title', ''),
                    iAbbrev, cAbbrev, cLang,
                    state.getMatchingPatterns(name), hasISO4Redirect)
            continue
        if iAbbrevDotless == iAbbrev:
            print('--Abbreviation is trivial (has no dots), '
                  + 'to avoid confusion we\'re ignoring [[' + title + ']].')
            skip = True
            report.reportTrivialAbbrev(
                title, infobox.get('title', ''),
                iAbbrev, pageData['redirects'])
        elif not hasISO4Redirect:
            iTitle = infobox.get('title', '')
            result[iAbbrev] = (rNewContent, iTitle)
            result[iAbbrevDotless] = (rNewContent, iTitle)
    return result, skip


def isValidISO4Redirect(rContent, title):
    """Return whether the content of a given redirect page is already
    just a simple variation of what we would put.

    `rContent` -- wikitext context of the redirect
    `title` -- title of the target page
    """
    # Ignore special characters variants.
    rContent = rContent.replace('&#38;', '&')
    rContent = rContent.replace('&#39;', '\'')
    rContent = rContent.replace('_', ' ')
    # Ignore double whitespace.
    rContent = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', rContent.strip())
    title = re.sub(r'((?<!\w)\s|\s(?![\s\w]))', '', title.strip())
    # Ignore capitalization.
    rContent = rContent.replace('redirect', 'REDIRECT')
    rContent = rContent.replace('Redirect', 'REDIRECT')
    # Ignore expected rcats.
    rContent = re.sub(r'{{R(EDIRECT)? (un)?printworthy}}', '', rContent)
    rContent = re.sub(r'{{R(EDIRECT)? u?pw?}}', '', rContent)
    rContent = re.sub(r'{{R from move}}', rContent)
    rContent = re.sub(r'{{R from bluebook}}', rContent)
    rContent = re.sub(r'{{R from MEDLINE abbreviation}}', rContent)
    # Ignore variants which include the rcat shell.
    rContent = rContent.replace('{{REDIRECT category shell',
                                '{{REDIRECT shell')
    # Ignore synonims of the rcat.
    rContent = rContent.replace('{{R from ISO 4 abbreviation',
                                '{{R from ISO 4')
    rWithoutShell = '#REDIRECT[[' + title + ']]{{R from ISO 4}}'
    rWithShell = '#REDIRECT[[' + title + ']]' \
                 + '{{REDIRECT shell|{{R from ISO 4}}}}'
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
    #    rContent = re.sub(r'{{R from[a-zA-Z4\s]*}}', '', rContent, 1)
    rContent = re.sub(r'{{R from (ISO 4|abb[a-z]*|shortening|initialism'
                      + r'|short name|alternat[a-z]* spelling'
                      + r'|systematic abbreviation|other capitalisation'
                      + '|other spelling)}}',
                      '',
                      rContent,
                      1)
    # Allow removing a common bug (an rcat without '{{}}').
    rContent = re.sub(r'R from abbreviation', '', rContent, 1)
    # Allow removing/adding the rcat shell.
    rContent = re.sub(r'{{REDIRECT shell\s*[|](1=)?\s*}}', '', rContent)
    rContent = re.sub(r'{{REDIRECT category shell\s*[|](1=)?\s*}}', '',
                      rContent)
    return rContent == '#REDIRECT[[' + title + ']]'


def getPagesWithInfoboxJournals(limit):
    """ Get generator yielding all Pages that include an {{infobox journal}}.
    """
    global site
    ns = site.namespaces['Template']  # 10
    template = pywikibot.Page(site, 'Template:Infobox journal', ns=ns)
    return template.embeddedin(
        filter_redirects=False,  # Omit redirects
        namespaces=0,  # Mainspace only
        total=limit,   # Limit total number of pages outputed
        content=True)  # Immediately fetch content (not sure if we want this?)
    # Yields ~7500 pages.
    # Another way to get pages including a template is the following wrapper:
    #   from pywikibot import pagegenerators as pg
    #   gen = pg.ReferringPageGenerator(template, onlyTemplateInclusion=True)
    # Alternatively we could try to iterate through categories, like this:
    #   cat = pywikibot.Category(site, 'Category:Name of category')
    #   'Category:Articles with missing ISO 4 redirects' yields ~2000.
    #   'Category:English-language_journals' yields ~6000.
    #   'Category:Academic journals' yields ????
    # In the last case you'd probably want to exclude the subcategory
    # 'Literary magazines' (in 'Humanities journals') which includes all kinds
    # of comic book magazines, for example.
    # To recurse, use (with `recurse`=depth limit, content=True?):
    #   for page in cat.articles(recurse=True, namespaces=0, pages=15000)
    # or
    #   gen = pagegenerators.CategorizedPageGenerator(
    #       cat, recurse=True, total=15000, namespaces=0)


def getInfoboxJournals(page):
    """Yields all {{infobox journal}}s used in `page`.

    Each as a dict from param to value."""
    # We could use the pywikibot interface mwparserfromhell instead, but it may
    # fall-back to regex, reorder parameters, and mwph is better documented.
    #   p = pywikibot.textlib.extract_templates_and_params(page.text)
    #   text = pywikibot.textlib.glue_template_and_params(p)
    p = mwparserfromhell.parse(normalize('NFC', page.text))

    # Iterate over {{infobox journal}} template instances on `page`.
    # We ignore synonims of [[Template:Infobox journals]], see:
    #   https://en.wikipedia.org/w/index.php?title=Special:WhatLinksHere/Template:Infobox_journal&hidetrans=1&hidelinks=1
    for t in p.filter_templates():
        # mwpfh only normalizes the first letter.
        if t.name.matches('infobox journal') or \
           t.name.matches('Infobox Journal'):
            infobox = {}
            for param in t.params:
                paramName = str(param.name).lower().strip()
                if paramName in ['title', 'issn', 'abbreviation', 'language',
                                 'country', 'former_name', 'bluebook']:
                    infobox[paramName] = re.sub(r'<!--.*-->', '', str(param.value)).strip()
            yield infobox


def getRedirectsToPage(pageTitle, namespaces=None, total=None, content=False):
    """Yields all pages that are redirects to `page`.

    Note that page.backlinks(filterRedirects=True) should not be used!
    It also returns pages that include a link to `page` and happend to
    be redirects to a different, unrelated page (e.g. every redirect
    from a Bluebook abbrev includes a [[Bluebook]] link).
        for r in page.backlinks(followRedirects=False, filterRedirects=True,
                                namespaces=0, total=100, content=True):
    Note also we disregard double redirects: these are few and
    eventually resolved by dedicated bots.
    """
    global site
    return site._generator(pywikibot.data.api.PageGenerator,
                           type_arg="redirects",
                           titles=pageTitle,
                           grdprop="pageid|title|fragment",
                           namespaces=namespaces,
                           total=total,
                           g_content=content)


if __name__ == "__main__":
    main()
