#!/bin/sh
git submodule update --init --recursive
npm install esprima
python3 -m pip install -r $PWD/requirements.txt
python3 $PWD/gadfly.py $@
python3 -m json.tool $PWD/gadfly.py.json > $PWD/gadfly.json

