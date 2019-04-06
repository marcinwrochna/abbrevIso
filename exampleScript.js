#!/usr/bin/env node
/**
 * AbbrevIso v1.0 JS lib for publication title abbreviation per ISO-4 standard.
 * Copyright (C) 2017 by Marcin Wrochna. MIT License, see file: LICENSE.
 * @fileoverview The script fills abbreviations into the python bot's JSON state
 * file.
 */
'use strict';
const fs = require('fs');
const AbbrevIso = require('../nodeBundle.js');

const recomputeAll = process.argv.includes('reset');

const ltwa = fs.readFileSync('../LTWA_20170914-modified.csv', 'utf8');
const shortWords = fs.readFileSync('../shortwords.txt', 'utf8');
const abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

const stateFileName = 'abbrevBotState.json';
let state = fs.readFileSync(stateFileName, 'utf8');
state = JSON.parse(state);

if (!('abbrevs' in state))
  throw new Error('Invalid bot state file.');

for (const title in state['abbrevs']) {
  if (!recomputeAll && typeof(state['abbrevs'][title]) === 'object')
    continue;
  const t = title.normalize('NFC');
  const result = {};
  result['all'] = abbrevIso.makeAbbreviation(t);
  result['eng'] = abbrevIso.makeAbbreviation(t, ['eng', 'mul', 'lat', 'und']);
  const matchingPatterns = abbrevIso.getMatchingPatterns(t);
  let s = '';
  for (const pattern of matchingPatterns)
    s += pattern.line + '\n';
  result['matchingPatterns'] = s;
  state['abbrevs'][title] = result;
}

fs.writeFileSync(stateFileName, JSON.stringify(state), 'utf8');
