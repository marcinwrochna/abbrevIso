# abbrevIso
Publication title abbreviation per [ISO-4](http://www.uai.cl/images/sitio/biblioteca/citas/ISO_4_1997en.pdf) standard.

This is a library for finding abbreviations of journal titles and searching [LTWA](http://www.issn.org/services/online-services/access-to-the-ltwa/) (List of Title Word Abbreviations).
Try it [live](https://www.mimuw.edu.pl/~mw290715/iso4/), also check there for caveats and an overview of ISO-4 rules.

_International Journal of Geographical Information Science → Int. J. Geogr. Inf. Sci._  
_Zeitschrift für deutsches Altertum und deutsche Literatur → Z. dtsch. Altert. dtsch. Lit._  
_4OR-A Quarterly Journal of Operations Research → 4OR-Q. J. Oper. Res._

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

## Running
The library is arranged in ECMAScript 6 modules, which are not well supported yet, so some simple repackaging is needed using [rollup.js](https://rollupjs.org/) (which can be installed via `sudo npm install --global rollup`).

Two files must also be loaded:
* the [LTWA](http://www.issn.org/services/online-services/access-to-the-ltwa/) in CSV format; the library comes with a slightly modified version fixing some obvious bugs in it.
* a list of _short words_ (articles, prepositions, conjuctions) that should be omitted from titles; the library comes with a list including English, French, German and Spanish ones. Since articles are actually handled a bit differently by the standard, they are hard-coded in the library.

### In browsers
`rollup AbbrevIso.js -o browserBundle.js --f iife --name AbbrevIso`

```html
<script src="browserBundle.js"></script>
<script>
	let ltwaAjax = $.ajax({
		mimeType: 'text/plain; charset=utf-8',
		url: 'LTWA_20160915-modified.csv',
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

### In Node.js
`rollup AbbrevIso.js -o nodeBundle.js --f cjs --name AbbrevIso`


```node
let fs = require('fs');
let AbbrevIso = require('./nodeBundle.js');

let ltwa = fs.readFileSync('LTWA_20160915-modified.csv', 'utf8');
let shortWords = fs.readFileSync('shortwords.txt', 'utf8');
abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

let s = 'International Journal of Geographical Information Science';
console.log(abbrevIso.makeAbbreviation(s));
```

