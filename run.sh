#!/bin/sh
# The quotes and the () at the end are crucial.
gunicorn --workers 4 --bind 0.0.0.0:8000 'app:create_app()' --access-logfile ./logs/gunicorn-access.log --error-logfile ./logs/gunicorn-error.log --capture-output --log-level debug 