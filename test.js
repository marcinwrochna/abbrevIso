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

let t = process.argv.slice(2).join(' ').trim();
if (t.length) {
    t = t.normalize('NFC');
    console.log('Abbreviation using all language rules:');
    console.log(abbrevIso.makeAbbreviation(t));
    console.log('Matching patterns:');
    const matchingPatterns = abbrevIso.getMatchingPatterns(t);
    for (const pattern of matchingPatterns)
        console.log(pattern.line);
    console.log('Possible compound patterns:');
    const compoundPatterns = abbrevIso.getMatchingPatterns(t, undefined, true);
    for (const pattern of compoundPatterns)
        if (!matchingPatterns.includes(pattern))
            console.log(pattern.line);
} else {
    let rl = require('readline').createInterface({
        input: fs.createReadStream('./tests.csv', { encoding: 'utf8' })
    });
    rl.on('line', (line) => {
        line = line.split('\t', 3);
        const abbrev = abbrevIso.makeAbbreviation(line[0]);
        if (abbrev !== line[1] && line[1] !== '???') {
            console.log(`Mismatch:\t${line[0]}\nIs:       \t${abbrev}\nShould be:\t${line[1]}`);
            if (line[2])
                console.log(line[2]);
            console.log('');
        }
    });
}

