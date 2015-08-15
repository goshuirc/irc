#!/usr/bin/env sh
pushd tests > /dev/null

rm -rf .coverage > /dev/null
coverage run "--include=*girc/*" -m unittest > /dev/null
coverage report -m

popd > /dev/null
