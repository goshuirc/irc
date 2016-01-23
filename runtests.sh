#!/usr/bin/env bash
pushd tests > /dev/null

rm -rf .coverage > /dev/null
coverage run --source girc -m unittest > /dev/null
coverage report -m
coverage html

popd > /dev/null
