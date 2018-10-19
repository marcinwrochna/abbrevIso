#!/usr/bin/python3
"""A bot for handling OMICS journal titles: adding redirects and hatnotes."""
import logging
import re
import sys

import pywikibot
import pywikibot.data.api

import state


# ==Some basic config==
# Max number of edits to make (in one run of the script).
EDITS_LIMITS = {'create': 60000, 'talk': 60000, 'fix': 60000, 'hatnote': 0}
EDITS_DONE = {'create': 0, 'talk': 0, 'fix': 0, 'hatnote': 0}
# If true, only print what we would do, don't edit.
ONLY_SIMULATE_EDITS = False
STATE_FILE_NAME = 'abbrevBotState.json'
# Whether to tag edits as 'bot trial' in Wikipedia.
BOT_TRIAL = False

# pywikibot's main object.
site = None


def main() -> None:
    """Execute the bot."""
    global site  # pylint: disable=global-statement
    logging.basicConfig(level=logging.WARNING)
    if len(sys.argv) != 2:
        print('Usage: ' + sys.argv[0] + ' filename.txt')
        return
    filename = sys.argv[1]

    state.loadOrInitState(STATE_FILE_NAME)
    site = pywikibot.Site('en')
 
    configLines = True
    numLines = num_lines = sum(1 for line in open(filename) if line.rstrip())
    i = 0
    with open(filename) as f:
        for title in f:
            title = title.strip()
            if not title:
                continue
            i += 1
            print('Line ' + str(i - 3) + '/' + str(numLines - 3) + ' \t [' + filename + ']')
            if configLines:
                if title == '---':
                    if not rTarget:
                        print('ERROR: Target not configured!')
                        break
                    targetPage = pywikibot.Page(site, rTarget)
                    if not targetPage.exists() or targetPage.isRedirectPage() or targetPage.isCategoryRedirect() or targetPage.isDisambig():
                        print('ERROR: target "' + rTarget +'" does not exists or is a redirect')
                        break
                    if not rCat:
                        print('WARNING: no category configured!')
                    else:
                        catPage = pywikibot.Page(site, 'Category:' + rCat)
                        if not catPage.exists() or not catPage.is_categorypage() or catPage.isCategoryRedirect():
                            print('ERROR: category "' + rCat +'" does not exist or is not category or is redirect')
                            break
                    print('Redirect target = [[' + rTarget + ']]')
                    print('Redirect cat = [[Category:' +rCat + ']]')
                    configLines = False
                    continue
                keyvalue = title.split('=', 2)
                if len(keyvalue) != 2:
                    print('ERROR: lines before "---" should be key=value config!')
                    break
                if keyvalue[0].strip() == 'target':
                    rTarget = keyvalue[1].strip()
                elif keyvalue[0].strip() == 'category':
                    rCat = keyvalue[1].strip()
                else:
                    print('ERROR: unrecognized configuration key "' + keyvalue[0] + '"')
                    break
            else:
                doOmicsRedirects(title, rTarget, rCat)
            # doOmicsHatnotes(title)
            sys.stdout.flush()
    state.saveState(STATE_FILE_NAME)


def doOmicsRedirects(title: str, rTarget: str, rCat: str) -> None:
    """Create redirects for given OMICS journal."""
    # If [[title]] exists, add '(journal)', unless its a redirect
    # (either one we did, maybe to be fixed, or an unexpected one we'll skip).
    addJournal = False
    if '(journal)' in title:
        title = title.replace('(journal)', '').strip()
        addJournal = True
    if '(' in title:
        print('Skip: [[' + title + ']] has unexpected disambuig.')
    page = pywikibot.Page(site, title)
    if page.exists() and not page.isRedirectPage():
        addJournal = True
        if 'journal' in title.lower():
            print('Skip: [[' + title + ']] already exists, '
                  'title already has "journal".')
            return
        for cat in page.categories():
            if 'journal' in cat.title().lower():
                print('Skip: [[' + title + ']] already exists, '
                      'has category containing "journal".')
                return

    # List of redirect pages to create, together with their type.
    rTitles = set([(title, 'plain')])

    # Handle 'and' vs '&' variant.
    if ' and ' in title:
        rTitles.add((title.replace(' and ', ' & '), 'and'))
    elif ' & ' in title and 'Acta' not in title:
        rTitles.add((title.replace(' & ', ' and '), 'and'))

    # Handle variant without 'The' at the beginning.
    if title.startswith('The '):
        rTitle = title.replace('The ', '')
        rTitles.add((rTitle, 'the'))
        if ' and ' in rTitle:
            rTitles.add((rTitle.replace(' and ', ' & '), 'theand'))
        elif ' & ' in rTitle and 'Acta' not in rTitle:
            rTitles.add((rTitle.replace(' & ', ' and '), 'theand'))

    # Handle ISO-4 abbreviated variants.
    state.saveTitleToAbbrev(title)
    try:
        cLang = 'all' if ('acta' in title.lower()) else 'eng'
        cAbbrev = state.getAbbrev(title, cLang)
    except state.NotComputedYetError as err:
        print(err.message)
        return
    if cAbbrev != title:
        rTitles.add((cAbbrev, 'iso4'))
        rTitles.add((cAbbrev.replace('.', ''), 'iso4'))

    # Skip if any of the redirect variants exists and is unfixable.
    for (rTitle, rType) in rTitles:
        if addJournal and rType != 'iso4':
            rTitle = rTitle + ' (journal)'

        r = createOmicsRedirect(rTitle, rType, rTarget, rCat, tryOnly=True)
        if r == 'unfixable':
            print('Skip: [[' + title + ']] unfixable.')
            return

    # Create the redirects.
    for (rTitle, rType) in rTitles:
        if addJournal and rType != 'iso4':
            rTitle = rTitle + ' (journal)'
        createOmicsRedirect(rTitle, rType, rTarget, rCat, tryOnly=False)

    # rPage = pywikibot.Page(site, rTitle)
    #     if rPage.exists():
    #         someExists = True
    #         if page.isRedirectPage():
    #             target = page.getRedirectTarget().title()
    #             if target == rTarget:
    #                 createOmicsRedirect(rTitle, rType, rTarget, rCat)
    #             elif target in ['Allied Academies',
    #                             'Pulsus Group',
    #                             'OMICS Publishing Group',
    #                             'Baishideng Publishing Group',
    #                             'Scientific Research Publishing']:
    #                 print('Done: [[' + title + ']] or variant already '
    #                       'redirects to OMICS-like.')
    #                 return
    #             else:
    #                 print('Skip: [[' + title + ']] redirects '
    #                       'to unexpected [[' + target + ']].')
    #                 return
    #         else:
    #             print('Skip: [[' + rTitle + ']] already exists.')
    #             return
    # if someExists:
    #     return


def doOmicsHatnotes(title: str) -> None:
    """Create hatnotes for given OMICS journal."""
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
                if not aPage.isRedirectPage():
                    addOmicsHatnote(aTitle, title)
            else:
                aTitle = aTitle + ' (journal)'
                aPage = pywikibot.Page(site, aTitle)
                if aPage.exists() and not aPage.isRedirectPage():
                    addOmicsHatnote(aTitle, title)


def addOmicsHatnote(aTitle: str, title: str) -> None:
    """Add hatnote to [[aTitle]] about confusion risk with OMICS [[title]]."""
    page = pywikibot.Page(site, aTitle)
    if '{{Confused|' in page.text or '{{confused|' in page.text:
        print('Skip: {{confused}} hatnote already on [[' + aTitle + ']]')
        return
    print('Adding hatnote to [[' + aTitle + ']]')
    hatnote = ('{{Confused|text=[[' + title + ']],'
               ' published by the [[OMICS Publishing Group]]}}\n')
    save(page, hatnote + page.text, overwrite=True, limitType='hatnote',
         summary='Add hatnote to predatory journal clone.')


def createOmicsRedirect(title: str, rType: str,
                        target: str, category: str, tryOnly: bool) -> str:
    """Attempt to create or fix redirect from [[title]] to [[target]].

    We return 'create' if non-existing, 'done' if basically equal to what we
    would add, 'fix' if exists but looks fixable, 'unfixable' otherwise.
    Also create talk page with {{WPJournals}} when non-existing.
    """
    rText = '#REDIRECT[[' + target + ']]\n'
    rCat = '[[Category:' + category + ']]\n' if category else ''
    rIsoCat = '{{R from ISO 4}}\n'
    rSortTitle = title
    if rSortTitle.startswith('The ') and '(' not in title:
        rSortTitle = rSortTitle.replace('The ', '') + ', The'
    if ' & ' in rSortTitle:
        rSortTitle = rSortTitle.replace(' & ', ' and ')
    if rSortTitle != title:
        rSort = '{{DEFAULTSORT:' + rSortTitle + '}}\n'

    rNewContent = rText
    if rSortTitle != title:
        rNewContent += rSort
    if rType == 'plain':
        rNewContent += rCat
    if rType == 'iso4':
        rNewContent += '{{R from ISO 4}}\n'

    rPage = pywikibot.Page(site, title)
    rTalkPage = rPage.toggleTalkPage()
    if not rPage.exists():
        if not tryOnly:
            print('Creating redirect from: [[' + title + ']].')
            save(rPage, rNewContent,
                 'Create redirect from predatory publisher\'s journal.',
                 overwrite=False, limitType='create')
            if rType == 'plain' and not rTalkPage.exists():
                content = '{{WPJournals|class=redirect}}'
                save(rTalkPage, content,
                     'Create redirect from predatory publisher\'s journal.',
                     overwrite=False, limitType='talk')
        return 'create'
    # If rPage exists, check if we would add basically the same.
    text = rPage.text
    if re.sub(r'\s', '', text, re.M).strip() == re.sub(r'\s', '', rNewContent, re.M).strip():
        if not tryOnly:
            if rTalkPage.exists():
                print('Done: [[' + title + ']].')
            elif rType == 'plain':
                print('Done, but creating talk page: [[' + title + ']].')
                content = '{{WPJournals|class=redirect}}'
                save(rTalkPage, content,
                     'Create redirect from predatory publisher\'s journal.',
                     overwrite=False, limitType='talk')
        return 'done'
    # If rPage exists but not the same, check if it is a fixable case.
    if rCat:
        text = text.replace(rCat.strip(), '')
    text = text.replace(rIsoCat.strip(), '')
    text = re.sub(r'\{\{DEFAULTSORT:[^\}]*\}\}', '', text)
    if re.sub(r'\s', '', text, re.M).strip() != re.sub(r'\s', '', rText, re.M).strip():
        print('Not fixable: [[' + title + ']]  (type=' + rType + ').')
        print('---IS-------------')
        print(rPage.text)
        print('---SHOULD BE------')
        print(rNewContent)
        print('==================')
        return 'unfixable'
    # If it is fixable, fix it.
    if not tryOnly:
        print('Fixing redirect from: [[' + title + ']] (type=' + rType + ').')
        print('---WAS------------')
        print(rPage.text)
        print('---WILL BE--------')
        print(rNewContent)
        print('==================')
        save(rPage, rNewContent,
             'Fix redirect from predatory publisher\'s journal.',
             overwrite=True, limitType='fix')
        if rType == 'plain' and not rTalkPage.exists():
            content = '{{WPJournals|class=redirect}}'
            save(rTalkPage, content,
                 'Fix redirect from predatory publisher\'s journal.',
                 overwrite=False, limitType='talk')
    return 'fix'


def save(page: pywikibot.Page, content: str,
         summary: str,
         overwrite: bool, limitType: str) -> bool:
    """Create or overwrite page with given content, checking bot limits."""
    global EDITS_DONE
    if ONLY_SIMULATE_EDITS:
        return False
    if limitType not in EDITS_LIMITS or limitType not in EDITS_DONE:
        raise Exception('Undefined limit type: "' + limitType + '"')
    if EDITS_DONE[limitType] >= EDITS_LIMITS[limitType]:
        return False
    EDITS_DONE[limitType] += 1
    page.text = content
    summary = ('[[Wikipedia:Bots/Requests_for_approval/TokenzeroBot_6|(6)]] ' +
               summary +
               ' [[User talk:TokenzeroBot|Report problems]].')
    page.save(summary,
              minor=False,
              botflag=True,
              watch="nochange",
              createonly=False if overwrite else True,
              nocreate=True if overwrite else False,
              tags='bot trial' if BOT_TRIAL else None)
    return True


if __name__ == "__main__":
    main()
