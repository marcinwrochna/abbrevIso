# wiki bot
This is a bot running on [Wikipedia](https://en.wikipedia.org) (as [TokenzeroBot](https://en.wikipedia.org/wiki/User:TokenzeroBot)) to check and fix redirects to academic journals, according to ISO-4 abbreviations.

It is written in Python 3 using the [pywikibot](https://github.com/wikimedia/pywikibot) and [mwparserfromhell](https://github.com/earwig/mwparserfromhell) libraries.
Since the abbrevISO library is impemented in JavaScript, the Python bot maintains a state in a .json file and a small Node.js script reads the required titles and writes computed abbreviations into the file.

## Running the bot
You will need to install the libraries: `pip install mwparserfromhell pywikibot` (possibly `pip3` with option `--user`)
and have AbbrevIso.js working: `rollup AbbrevIso.js -o nodeBundle.js --f cjs --name AbbrevIso`

Pywikibot requires [some configuration](https://github.com/wikimedia/pywikibot), you can test it by running `python3 wikiBot.py test` (change the code for the write to be non-trivial).

Run `python3 wikiBot.py scrape` to scrape all the required pages and redirects. There are around 7500 pages and roughly 2 redirects per page, so with pywikibot defaults this runs about an hour.
The state file is now full.

Run `./abbrevIsoBot.js` to compute the abbreviations in the state file. The first time is very resource-intensive, it may take another hour. Rerunning the script will only compute missing abbreviations. To recompute all, run `./abbrevIsoBot.js reset`.

Run `python3 wikiBot.py fixpages` to scrape again, making fixes along the way according to computed abbrevs and make the reports.

Run `python3 wikiBot.py report` to do the same, but only simulating edits: we only write the reports.
Since both `fixpages` and `report` scrape evertyhing, you don't need to run `scrape` again. You will need to run `./abbrevIsoBot.js` in case new titles appear.

See the code (`wikiBot.py`) for some basic configuration and more.
