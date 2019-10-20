# abbrevIso
Publication title abbreviation per [ISO-4](https://web.archive.org/web/20180328190032/http://www.uai.cl/images/sitio/biblioteca/citas/ISO_4_1997en.pdf/) standard.
Try it [live](https://marcinwrochna.github.io/abbrevIso/)!

This is a library for finding abbreviations of journal titles and searching [LTWA](http://www.issn.org/services/online-services/access-to-the-ltwa/) (List of Title Word Abbreviations).
See [here](https://marcinwrochna.github.io/abbrevIso/) for an overview of ISO-4 rules and caveats.
Or try [the API](https://tools.wmflabs.org/abbreviso/) instead.

_International Journal of Geographical Information Science → Int. J. Geogr. Inf. Sci._  
_Zeitschrift für deutsches Altertum und deutsche Literatur → Z. dtsch. Altert. dtsch. Lit._  
_4OR-A Quarterly Journal of Operations Research → 4OR-Q. J. Oper. Res._

There is also a [Python bot](https://github.com/marcinwrochna/tokenzeroBot/tree/master/abbrevIsoBot) using this library for maintaining redirects on Wikipedia.

## Using
`abbrevIso.makeAbbreviation(s)` outputs the computed abbreviation for the given title `s`.

`abbrevIso.getMatchingPatterns(s)` returns all patterns matching `s`, sorted by start index of match.
The patterns are returned as a list of objects with the following properties:
 * pattern – the actual pattern string from the LTWA, with dashes;
 * replacement – the replacement string from the LTWA;
 * languages – an array of language codes to which the pattern applies;
 * startDash, endDash – booleans telling whether the pattern has dashes;
 * line – the original full line from the LTWA.

Both functions accept an optional `languages` parameter, an `Array` of [ISO-639-2 (B)](https://www.loc.gov/standards/iso639-2/php/code_list.php) language codes. If given, only LTWA patterns that apply to at least one of these languages are used.
If not given, all patterns are used. A recommended option for English titles is `['eng', 'mul', 'lat', 'und']` (for English, multilanguage, Latin, and undefined languages – in case some LTWA bugs are relevant to you).

The library is designed for mass use, so the abbrevIso object is created once, slowly generating an index, but once this is done, queries should be fast.

## Running
You need 3 files to run the library yourself:
* the bundled library: either `browserBundle.js` (for browsers) or `nodeBundle.js` (for Node.js)
* the [LTWA](http://www.issn.org/services/online-services/access-to-the-ltwa/) in CSV format; the library comes with a slightly modified version fixing some obvious bugs in it: `LTWA_20170914-modified.csv`
* a list of _short words_ (articles, prepositions, conjuctions) that should be omitted from titles; the library comes with a list including English, French, German and Spanish ones: `shortwords.txt` (Since articles are actually handled a bit differently by the standard, they are hard-coded in the library.)

### In browsers
The library can be run in a browser as follows (loading auxilliary files using jQuery ajax):
```html
<script
	src="https://code.jquery.com/jquery-3.3.1.min.js"
	integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8="
	crossorigin="anonymous"></script>
<script src="browserBundle.js"></script>
<script>
	let ltwaAjax = $.ajax({
		mimeType: 'text/plain; charset=utf-8',
		url: 'LTWA_20170914-modified.csv',
		dataType: 'text',
	});
	let shortWordsAjax = $.ajax({
		mimeType: 'text/plain; charset=utf-8',
		url: 'shortwords.txt',
		dataType: 'text',
	});
	$.when(ltwaAjax, shortWordsAjax).done( (ltwa, shortWords) => {
		abbrevIso = new AbbrevIso.AbbrevIso(ltwa[0], shortWords[0]);
		let s = 'International Journal of Geographical Information Science';
		console.log(abbrevIso.makeAbbreviation(s));
	});
</script>  
```
Note that the ajax may fail if loading this locally using `file://` in Chrome.
You can instead start a basic server that will host the current working directory at `http://localhost:8000` simply by running `python3 -m http.server`.

### In Node.js
You can run the library on any PC as follows:
* install [Node.js](https://nodejs.org/en/) (from the Windows installer or from your Linux repository)
* download (or git clone) the 3 files
* write an example script using the library:

```node
let fs = require('fs');
let AbbrevIso = require('./nodeBundle.js');

let ltwa = fs.readFileSync('LTWA_20170914-modified.csv', 'utf8');
let shortWords = fs.readFileSync('shortwords.txt', 'utf8');
let abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

let s = 'International Journal of Geographical Information Science';
console.log(abbrevIso.makeAbbreviation(s));
```
* run the script: `node example.js`
* to use with other languages, you can use your language to write a JSON file with a list of titles to be abbreviated, fill the JSON file with abbreviations with a simple JavaScript script (like [here](exampleScript.js)) and read the resulting JSON file back in your language.

## Compiling (bundling/repackaging)
In case you need to change the library, you will need to repackage it. 
This is because the library is arranged in ECMAScript 6 modules, which are not well supported yet.
Fortunately it suffices to repackage it using [rollup.js](https://rollupjs.org/) (which can be installed from your repository or using npm, the Node.js package manager, like: `sudo npm install --global rollup`).

To create the browser bundle:

`rollup AbbrevIso.js -o browserBundle.js --f iife --name AbbrevIso`

To create the Node.js bundle:

`rollup AbbrevIso.js -o nodeBundle.js --f cjs --name AbbrevIso`
