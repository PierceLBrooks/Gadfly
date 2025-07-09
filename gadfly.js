var esprima = require('esprima');
const fs = require('fs');
const js_file_string = fs.readFileSync(process.argv[2], 'utf8');
console.log(JSON.stringify(esprima.parse(js_file_string), null, 2));

