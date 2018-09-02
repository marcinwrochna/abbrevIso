# -*- coding: utf-8 -*-
"""A module for the state, shared between runs and with abbrevIsoBot.js."""

import json
from typing import Any, Dict

# `state` is a global variable maintained between runs.
# state = {
#     'pages': {
#         'Wiki Page Title': {
#             'infoboxes': [{'title': 'IJ Title',
#                            'issn': ...,
#                            'abbreviation': ...,
#                            ...},
#                           ...
#             ],
#             'redirects': {
#                 'Redirect Page Title': 'Redirect Page Wikitext Content',
#                 ...
#             },
#         },
#         ...
#     },
#     'abbrevs': {
#         'Wiki Page or Infobox Tile': {
#             'eng': 'abbrevISO-computed abbreviation
#                 using only eng,mul,lat,und LTWA rules',
#             'all': 'using all rules'
#         },
#         ...
#     }
__state = {}  # type: Dict[str, Dict[str, Any]]


def loadOrInitState(stateFileName: str) -> None:
    """Load `state` from `STATE_FILE_NAME` or create a new one."""
    global __state  # pylint: disable=global-statement
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


def saveState(stateFileName: str) -> None:
    """Save `state` to `STATE_FILE_NAME`."""
    with open(stateFileName, 'wt') as f:
        json.dump(__state, f)


def dump() -> str:
    """Return formatted JSON of the state."""
    return json.dumps(__state, indent="\t")


def saveTitleToAbbrev(title: str) -> None:
    """Save `title` for computing its abbrev later, by running abbrevIso.js."""
    if title not in __state['abbrevs']:
        __state['abbrevs'][title] = False


class NotComputedYetError(LookupError):
    """Raised when abbreviations for a title have not been computed yet."""

    def __init__(self, title: str) -> None:
        super().__init__(title)
        self.message = ('No computed abbreviation stored for "' + title + '", '
                        'please rerun abbrevIsoBot.js .')


def hasAbbrev(title: str) -> bool:
    """Return whetever the abbrev for given title is saved and computed."""
    return (title in __state['abbrevs'] and
            __state['abbrevs'][title] is not False)


def getAbbrev(title: str, language: str) -> str:
    """Return abbreviation for given (page or infobox) title.

    `language` should be 'all' or 'eng', depending on which LTWA rules to use.
    """
    if title not in __state['abbrevs'] or not __state['abbrevs'][title]:
        raise NotComputedYetError(title)
    return __state['abbrevs'][title][language]


def getAllAbbrevs(title: str) -> Dict[str, str]:
    """Return dict from language to abbrev, for a given title to abbreviate."""
    if title not in __state['abbrevs'] or not __state['abbrevs'][title]:
        raise NotComputedYetError(title)
    result = __state['abbrevs'][title].copy()
    result.pop('matchingPatterns')
    return result


def getMatchingPatterns(title: str) -> str:
    """Return matching LTWA patterns for given title to abbreviate."""
    if title not in __state['abbrevs'] or not __state['abbrevs'][title]:
        raise NotComputedYetError(title)
    return __state['abbrevs'][title]['matchingPatterns']


def savePageData(pageTitle: str, pageData: Dict[str, Any]) -> None:
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
    __state['pages'][pageTitle] = pageData


def getPageData(pageTitle: str) -> Dict[str, Any]:
    """Return latest saved page data (in a scrape run of the script)."""
    return __state['pages'][pageTitle]


def getPagesDict() -> Dict[str, Dict[str, Any]]:
    """Return dictionary from pageTitle to pageData."""
    return __state['pages']
