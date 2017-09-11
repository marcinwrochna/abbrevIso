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
abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

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
	if (totalCount > 20)
		break;
	totalCount++;
	console.warn('Testing ' + totalCount + ': '+ testCase);
	
	let test = testCase.split('\t');
	if (test[2] == 'NULL' || test[2].trim().length == 0) {
		nullAbbrv++;
		continue;
	}
	
	let value = test[1].normalize('NFC').trim();
	// If no infobox title, use wiki page title, removing disambigs like '(journal)'.
	if (value == 'NULL' || value.length == 0)
		value = test[0].normalize('NFC').trim().replace(/\s*\(.*\)/, ''); 
	let result = abbrevIso.makeAbbreviation(value);
	if (result === test[2].normalize('NFC').trim() ||
			// Allow passing the test if removing dependent part and comments (parens) helps.
			result.replace(/\s*:.+/, '') === test[2].normalize('NFC').trim().replace(/\s*\(.+/, ''))
		successCount++;
	else {
		failCount++;
		if (test[1] == test[0] || test[1] == 'NULL' || test[1].trim().length == 0)
			test[1] = '';
		if (test[3] == 'NULL' || test[3].trim().length == 0)
			test[3] = '';
		if (test[4] == 'NULL' || test[4].trim().length == 0)
			test[4] = '';
		let applied = '<pre>';
		let matchingPatterns = abbrevIso.getMatchingPatterns(value);
		for (const pattern of matchingPatterns) {
			applied += pattern[0] + '\t' + pattern[1] + '\t' + pattern[2] + '\n';
		}
		applied += '</pre>';
		if (failCount < 250)
		table += '|-\n| [[' + test[0] + ']]\n| ' + test[1] + '\n| ' + test[2] + '\n' +
				'| ' + result + '\n| ' + test[3] + '\n| ' + test[4] + '\n| ' + applied + '\n| \n';
		//table += '|-\n{{ISO 4 mismatch |pagename=' + test[0] + ' |title=' + test[1] +
		//		' |abbreviation=' + test[2] + ' |bot-guess=' + result + ' |language=' + test[3] +
		//		' |country=' + test[4] + ' |matches=' + applied + '}}\n';
	}
}
table += '|}\n';

console.log(table);
console.warn('Of ' + totalCount + ' tests, ' + nullAbbrv + ' nulls, ' +
		successCount + ' successes, ' + failCount + ' mismatches.');
