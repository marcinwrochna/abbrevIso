#!/usr/bin/env node
/**
 * AbbrevIso v1.0 JS lib for publication title abbreviation per ISO-4 standard.
 * Copyright (C) 2017 by Marcin Wrochna. MIT License, see file: LICENSE.
 * @fileoverview Prefix trees for quickly finding patterns.
 */
'use strict';
let fs = require('fs');
let AbbrevIso = require('./nodeBundle.js');

let ltwa = fs.readFileSync('LTWA_20160915-modified.csv', 'utf8');
let shortWords = fs.readFileSync('shortwords.txt', 'utf8');
let abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

//console.log(abbrevIso.makeAbbreviation('International Journal of Geographical Information Science'));

let args =  process.argv.slice(2);
let testCases = fs.readFileSync(args[0], 'utf8');
testCases = testCases.split(/\r\n|[\n\v\f\r\x85\u2028\u2029]/);
//process.stdin.setEncoding('utf8');

let totalCount = 0;
let nullAbbrv = 0;
let successCount = 0;
let failCount = 0;
let table = '{| class="wikitable"\n|-\n!page title\n!infobox title\n' +
	'!infobox abbrv\n!bot guess\n!validate\n!infobox lang\n!infobox country\n'+
	'! scope="column" style="width: 400px;" | LTWA patterns applied\n!comment\n';


for (const testCase of testCases) {
	// Skip csv header and empty lines.
	if (testCase[0] == '#' || testCase.trim().length == 0)
		continue;
	// Limit number of tests executed.
	if (totalCount > 1000)
		break;
	totalCount++;
	console.warn('Testing ' + totalCount + ': '+ testCase);

	let test = testCase.split('\t');
	let title = test[2].normalize('NFC').trim();
	// Discard disambigs like '(journal)'.
	let wikititle = test[0].normalize('NFC').trim().replace(/\s*\(.*\)/, '');
	let value = title;
	// If no infobox title, use wiki page title.
	if (value == 'NULL' || value.length == 0)
		value = wikititle;
	let infoboxID = test[1].normalize('NFC').trim();
	let abbrv = test[4].normalize('NFC').trim();
	let language = test[5].normalize('NFC').trim();
	let country = test[6].normalize('NFC').trim() ;

	if (abbrv == 'NULL' || abbrv.trim().length == 0) {
		nullAbbrv++;
		continue;
	}
	const engCountries = ['United States', 'U.S.', 'U. S.', 'USA', 'U.S.A', 'US',
		'United Kingdom', 'UK', 'New Zealand', 'Australia', 'UK & USA', 'England'];
	let assumeEnglish = false;
	if (language.trim().length < 2 ||
			language.startsWith('English') ||
			language == 'NULL')
		assumeEnglish = true;
	assumeEnglish = assumeEnglish && (engCountries.indexOf(country) >= 0);
	let languages = assumeEnglish ? ['eng', 'mul', 'lat', 'und'] : undefined;

	let result = abbrevIso.makeAbbreviation(value, languages);
	// Allow passing the test if removing dependent part and comments (parens) helps.
	if (result === abbrv || result.replace(/\s*:.+/, '') === abbrv.replace(/\s*\(.+/, '')) {
		successCount++;
	} else {
		failCount++;
		if (title == wikititle || title == 'NULL' || title.length == 0)
			title = '';
		if (language == 'NULL' || language.length == 0)
			language = '';
		if (country == 'NULL' || country.length == 0)
			country = '';
		let applied = '<pre>';
		let matchingPatterns = abbrevIso.getMatchingPatterns(value);
		for (const pattern of matchingPatterns) {
			applied += pattern.line + '\n';
		}
		applied += '</pre>';
		let comment = '';
		if (infoboxID != 1)
			comment = 'j.-infobox-#' + (new String(infoboxID));
		// Only output the first few mismatches.
		if (failCount < 100)
		//	table += '|-\n| [[' + wikititle + ']]\n| ' + title + '\n| ' + abbrv + '\n' +
		//		'| ' + result + '\n| ' + language + '\n| ' + country + '\n| ' + applied + '\n| \n';
			table += '|-\n{{ISO 4 mismatch |pagename=' + wikititle + ' |title=' + title +
					' |abbreviation=' + abbrv + ' |bot-guess=' + result + '}}\n' +
					'| ' + language + '\n| ' + country + '\n| ' + applied + '\n'+
					'| ' + comment + '\n';
	}
}
table += '|}\n';
// {| id="toc" border="0"
//! '''Mismatches''': &nbsp;
//| 0xx [[/ISO_4/1|1xx]] [[/ISO_4/1|1xx]]... &nbsp;|}

console.log(table);
console.warn('Of ' + totalCount + ' tests, ' + nullAbbrv + ' nulls, ' +
		successCount + ' successes, ' + failCount + ' mismatches.');
