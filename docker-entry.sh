#!/bin/bash

exec gunicorn -c assets/gunicorn-conf.py 'git_archiver:app'
