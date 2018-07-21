#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
A bot for handling OMICS journal titles: adding redirects and hatnotes.
"""
import logging

import pywikibot
import pywikibot.data.api

import state


# ==Some basic config==
# Max number of pages to scrape.
SCRAPE_LIMIT = 10000
# Max number of edits to make (in one run of the script).
PLAIN_EDIT_LIMIT = 1
PLAIN_EDIT_DONE = 0
JOURNAL_EDIT_LIMIT = 1
JOURNAL_EDIT_DONE = 0
HATNOTE_EDIT_LIMIT = 1
HATNOTE_EDIT_DONE = 0
# If true, only print what we would do, don't edit.
ONLY_SIMULATE_EDITS = True
STATE_FILE_NAME = 'abbrevBotState.json'

# pywikibot's main object.
site = None


def main() -> None:
    """The main function."""
    global site  # pylint: disable=global-statement
    logging.basicConfig(level=logging.WARNING)
    state.loadOrInitState(STATE_FILE_NAME)
    site = pywikibot.Site('en')
    with open('omics.txt') as f:
        for title in f:
            doOmicsRedirects(title)
            doOmicsHatnotes(title)
    state.saveState(STATE_FILE_NAME)


def doOmicsRedirects(title: str) -> None:
    """Create redirects for given OMICS journal."""
    title = title.strip()
    # If [[title]] exists and is not a redirect, add '(journal)'
    addJournal = False
    page = pywikibot.Page(site, title)
    if page.exists():
        addJournal = True
        if page.isRedirectPage():
            target = page.getRedirectTarget().title()
            if target in ['Allied Academies',
                          'Pulsus Group',
                          'OMICS Publishing Group']:
                print('Done: [[' + title + ']] already redirects '
                      'to OMICS-like.')
                return
            else:
                print('Skip: [[' + title + ']] redirects '
                      'to unexpected [[' + target + ']].')
                return
        if 'journal' in title.lower():
            print('Skip: [[' + title + ']] already exists, '
                  'title already has "journal".')
            return

    rTitles = set([title])

    # Also handle 'and' vs '&' variant.
    if ' and ' in title:
        rTitles.add(title.replace(' and ', ' & '))
    elif ' & ' in title and 'Acta' not in title:
        rTitles.add(title.replace(' & ', ' and '))

    # Create ISO-4 redirects, enable multiling for 'Acta'
    state.saveTitleToAbbrev(title)
    try:
        cLang = 'all' if ('acta' in title.lower()) else 'eng'
        cAbbrev = state.getAbbrev(title, cLang)
    except state.NotComputedYetError:
        print('No computed abbreviation stored for "' + title + '", '
              'please rerun abbrevIsoBot.js .')
        return
    rTitles.add(cAbbrev)

    # Skip if any of the redirect titles already exists.
    skip = False
    for rTitle in rTitles:
        if addJournal:
            rTitle = rTitle + ' (journal)'
        if pywikibot.Page(site, rTitle).exists():
            print('Skip: [[' + rTitle + ']] already exists.')
            skip = True
            break
    if skip:
        return

    # Create the redirects.
    for rTitle in rTitles:
        if addJournal:
            rTitle = rTitle + ' (journal)'
        createOmicsRedirect(rTitle)


def doOmicsHatnotes(title: str) -> None:
    """Create hatnotes for given OMICS journal."""
    title = title.strip()
    # Create hatnotes for misleading (predatory) titles.
    suffixes = [': Open Access', '-Open Access',
                ': An Indian Journal', ': Current Research']
    aTitle = ''
    for s in suffixes:
        if title.endswith(s):
            aTitle = title[:-len(s)].strip()
    if aTitle:
        aPage = pywikibot.Page(site, aTitle)
        if aPage.exists():
            isJournal = False
            for cat in aPage.categories():
                if 'journal' in cat.title().lower():
                    isJournal = True
                    break
            if isJournal:
                addOmicsHatnote(aTitle, title)
            else:
                aTitle = aTitle + ' (journal)'
                if pywikibot.Page(site, aTitle).exists():
                    addOmicsHatnote(aTitle, title)


def addOmicsHatnote(aTitle: str, title: str) -> None:
    """Add hatnote to [[aTitle]] warning about possible confusion
    with OMICS [[title]].
    """
    print('Adding hatnote to [[' + aTitle + ']]')
    if not ONLY_SIMULATE_EDITS:
        global HATNOTE_EDIT_DONE
        HATNOTE_EDIT_DONE = HATNOTE_EDIT_DONE + 1
        if HATNOTE_EDIT_DONE > HATNOTE_EDIT_LIMIT:
            return
        hatnote = (
            '{{Confused|text=[[' + title + ']],'
            ' published by the [[OMICS Publishing Group]]}}\n')
        page = pywikibot.Page(site, aTitle)
        if '{{Confused|' in page.text or '{{confused|' in page.text:
            print('Skip: {{confused}} hatnote already on [[' + aTitle + ']]')
            return
        page.text = hatnote + page.text
        page.save(
            'Add hatnote to OMICS predatory clone. '
            'Report bugs and suggestions '
            'to [[User talk:TokenzeroBot]]',
            minor=False,
            botflag=True,
            watch="nochange",
            nocreate=True)


def createOmicsRedirect(rTitle: str) -> None:
    """Create redirect from [[rTitle]] to [[OMICS Publishing Group]].
    Also create talk page with {{WPJournals}}
    """
    print('Creating redirect from [[' + rTitle + ']]')
    rNewContent = (
        '#REDIRECT[[OMICS Publishing Group]]\n'
        '[[Category:OMICS Publishing Group academic journals]]\n')
    rNewTalkContent = '{{WPJournals}}'
    if not ONLY_SIMULATE_EDITS:
        if 'journal' in rTitle:
            global JOURNAL_EDIT_DONE
            JOURNAL_EDIT_DONE = JOURNAL_EDIT_DONE + 1
            if JOURNAL_EDIT_DONE > JOURNAL_EDIT_LIMIT:
                return
        else:
            global PLAIN_EDIT_DONE
            PLAIN_EDIT_DONE = PLAIN_EDIT_DONE + 1
            if PLAIN_EDIT_DONE > PLAIN_EDIT_LIMIT:
                return
        rPage = pywikibot.Page(site, rTitle)
        rPage.text = rNewContent
        rPage.save(
            'Creating redirect from OMICS journal. '
            'Report bugs and suggestions '
            'to [[User talk:TokenzeroBot]]',
            minor=False,
            botflag=True,
            watch="nochange",
            createonly=True)
        rTalkPage = rPage.toggleTalkPage()
        rTalkPage.text = rNewTalkContent
        rTalkPage.save(
            'Creating redirect from OMICS journal. '
            'Report bugs and suggestions '
            'to [[User talk:TokenzeroBot]]',
            minor=False,
            botflag=True,
            watch="nochange",
            createonly=True)


if __name__ == "__main__":
    main()
