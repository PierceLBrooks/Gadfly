#!/bin/sh
git submodule update --init --recursive
npm install esprima
python3 -m pip install -r $PWD/requirements.txt
python3 -d $PWD/gadfly.py $@ 2>&1 | tee $PWD/run.log
python3 -m json.tool $PWD/gadfly.py.json > $PWD/gadfly.json

