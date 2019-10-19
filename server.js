#!/usr/bin/env node
const express = require('express');
const fs = require('fs');
const AbbrevIso = require('./nodeBundle.js');
const bunyan = require('bunyan');
var log = bunyan.createLogger({
    name: 'abbrevisoApp',
    serializers: {req: bunyan.stdSerializers.req}
});

const app = express();
const port = process.env.PORT || 5000;

const ltwa = fs.readFileSync(__dirname + '/LTWA_20170914-modified.csv', 'utf8');
const shortWords = fs.readFileSync(__dirname + '/shortwords.txt', 'utf8');
const abbrevIso = new AbbrevIso.AbbrevIso(ltwa, shortWords);

app.get('/', function(req, res) {
    res.sendFile('server.html', { 'root': __dirname });
});

app.get('/a/*', function(req, res) {
    const title = req.params[0];
    let lang = req.query.lang;
    if (lang === 'all')
        lang = undefined;
    log.info({ title: title, lang: lang, req: req });
    const abbrev = abbrevIso.makeAbbreviation(title, lang);
    res.send(abbrev);
});

wrapper = express();
wrapper.use('/abbreviso', app);
wrapper.use('/', app);
wrapper.listen(port, () => console.log(`AbbrevIso listening on port ${port}!`));