# -*- coding: utf-8 -*-
""" A module for the state, shared between runs and with abbrevIsoBot.js."""

import json

"""`state` is a global variable maintained between runs.
    state = {
        'pages': {
            'Wiki Page Title': {
                'infoboxes': [{'title': 'IJ Title',
                               'issn': ...,
                               'abbreviation': ...,
                               ...},
                              ...
                ],
                'redirects': {
                    'Redirect Page Title': 'Redirect Page Wikitext Content',
                    ...
                },
            },
            ...
        },
        'abbrevs': {
            'Wiki Page or Infobox Tile': {
                'eng': 'abbrevISO-computed abbreviation
                    using only eng,mul,lat,und LTWA rules',
                'all': 'using all rules'
            },
            ...
        }
"""
__state = {}


def loadOrInitState(stateFileName):
    """Load `state` from `STATE_FILE_NAME` or create a new one."""
    global __state
    opened = False
    try:
        with open(stateFileName, 'rt') as f:
            opened = True
            __state = json.load(f)
    except IOError:
        # If there's an error after opening, when reading, we don't catch the
        # exception but fail instead, so the state file is not overwritten.
        if opened:
            raise
        else:
            print('Initiating empty bot state.')
            __state = {'pages': {}, 'abbrevs': {}}


def saveState(stateFileName):
    """Save `state` to `STATE_FILE_NAME`."""
    with open(stateFileName, 'wt') as f:
        json.dump(__state, f)


def dump():
    """Return formatted JSON of the state."""
    return json.dumps(__state, indent="\t")


def saveTitleToAbbrev(title):
    """Save `title` for computing its abbrev later, by running abbrevIso.js."""
    global __state
    if title not in __state['abbrevs']:
        __state['abbrevs'][title] = False


class NotComputedYetError(LookupError):
    """Raised when abbreviations for a title have not been computed yet."""


def hasAbbrev(name):
    """Return whetever the abbrev for given name is saved and computed."""
    return name in __state['abbrevs'] and __state['abbrevs'][name] is not False


def getAbbrev(name, language):
    """Return abbreviation for given name (page or infobox title).

    `language` should be 'all' or 'eng', depending on which LTWA rules to use.
    """
    if name not in __state['abbrevs'] or not __state['abbrevs'][name]:
        raise NotComputedYetError
    return __state['abbrevs'][name][language]
    # TODO make name, pageTitle, title, ... consistent


def getAllAbbrevs(name):
    """Return dict from language to abbrev, for a given name to abbreviate."""
    if name not in __state['abbrevs'] or not __state['abbrevs'][name]:
        raise NotComputedYetError
    result = __state['abbrevs'][name].copy()
    result.pop('matchingPatterns')
    return result


def getMatchingPatterns(name):
    """Return matching LTWA patterns for given name (title) to abbreviate."""
    if name not in __state['abbrevs'] or not __state['abbrevs'][name]:
        raise NotComputedYetError
    return __state['abbrevs'][name]['matchingPatterns']


def savePageData(pageTitle, pageData):
    """Save a scraped page's data.

    `pageData` is of the following form:
        {'infoboxes': [
                {'title': .., 'abbreviation': .., 'issn': .., ...},
                ...
            ],
         'redirects': {
                redirectTitle: redirectContent,
                ...
            }
        }
    """
    global __state
    __state['pages'][pageTitle] = pageData


def getPageData(pageTitle):
    """Return latest saved page data (in a scrape run of the script)."""
    return __state['pages'][pageTitle]


def getPagesDict():
    """Return dictionary from pageTitle to pageData."""
    return __state['pages']
