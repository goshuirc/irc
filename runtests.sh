#!/usr/bin/env bash

coverage run --source girc -m unittest > /dev/null
coverage report -m
coverage html
