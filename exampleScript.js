#!/usr/bin/env node
/**
 * @fileoverview Node.js script filling given JSON file with abbreviations.
 *
 * It expects a JSON object with a key 'abbrev', like:
 * {
 *  'abbrevs': {
 *    'Journal of Foo': {},
 *    'Journal of Bar': {},
 *    ...
 *  },
 *  ...
 * }
 * Under 'abbrevs', an object maps titles to abbreviation data.
 * When empty (or when 'reset' is given), this data is replaced by:
 *  {
 *    'all': 'abbrev using all language rules',
 *    'eng': 'abbrev using eng, mul (multilanguage) and lat (Latin) rules',
 *    'matchingPatterns': 'LTWA lines whose patterns matched, one per line'
 *  }
 * The speed is roughly 1h for 10000 titles.
 */
'use strict';
const fs = require('fs');
const AbbrevIso = require('./nodeBundle.js');

// Parse command-line arguments.
if (process.argv.length < 3 || process.argv[2] == 'reset')
  throw new Error('No filename given.');
const stateFileName = process.argv[2];
const recomputeAll = process.argv.includes('reset');

// Open JSON 'state' file.
let state = fs.readFileSync(stateFileName, 'utf8');
state = JSON.parse(state);
if (!(state instanceof Object) || !('abbrevs' in state))
  throw new Error('Invalid file: expected object with "abbrevs" key.');

// Load abbrevISO.
const ltwa = fs.readFileSync(__dirname + '/LTWA_20170914-modified.csv', 'utf8');
const shortWords = fs.readFileSync(__dirname + '/shortwords.txt', 'utf8');
const abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

// Compute the data in state['abbrevs'][title] for all titles.
for (const title in state['abbrevs']) {
  if (!recomputeAll
      && typeof(state['abbrevs'][title]) === 'object'
      && 'all' in state['abbrevs'][title])
    continue;
  const t = title.normalize('NFC');
  console.log(t);
  const result = {};
  result['all'] = abbrevIso.makeAbbreviation(t);
  result['eng'] = abbrevIso.makeAbbreviation(t, ['eng', 'mul', 'lat']);
  const matchingPatterns = abbrevIso.getMatchingPatterns(t);
  let s = '';
  for (const pattern of matchingPatterns)
    s += pattern.line + '\n';
  result['matchingPatterns'] = s;
  state['abbrevs'][title] = result;
}

// Save JSON 'state' file.
fs.writeFileSync(stateFileName, JSON.stringify(state), 'utf8');
