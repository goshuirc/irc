#!/usr/bin/env bash
pushd tests > /dev/null

rm -rf .coverage > /dev/null
coverage run "--include=*girc/*" "--omit=*env/*" -m unittest > /dev/null
coverage report -m
coverage html

popd > /dev/null
