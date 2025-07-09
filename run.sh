#!/bin/sh
git submodule update --init --recursive
npm install esprima
python3 -m pip install -r $PWD/requirements.txt
python3 $PWD/gadfly.py $@

