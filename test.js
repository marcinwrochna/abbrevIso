#!/usr/bin/env node
/**
 * AbbrevIso v1.0 JS lib for publication title abbreviation per ISO-4 standard.
 * Copyright (C) 2018 by Marcin Wrochna. MIT License, see file: LICENSE.
 * @fileoverview A test script for the library.
 */
'use strict';
const fs = require('fs');
const AbbrevIso = require('./nodeBundle.js');

const ltwa = fs.readFileSync('./LTWA_20170914-modified.csv', 'utf8');
const shortWords = fs.readFileSync('./shortwords.txt', 'utf8');
const abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

let t = process.argv.slice(2).join(' ');
t = t.normalize('NFC');
console.log('Abbreviation using all language rules:');
console.log(abbrevIso.makeAbbreviation(t));
console.log('Abbreviation using only english rules:');
console.log(abbrevIso.makeAbbreviation(t, ['eng', 'mul', 'lat', 'und']));
console.log('Matching patterns:');
const matchingPatterns = abbrevIso.getMatchingPatterns(t);
for (const pattern of matchingPatterns) {
    console.log(pattern.line);
}

