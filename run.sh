#!/bin/sh
# The quotes and the () at the end are crucial.
gunicorn --workers 4 --bind 0.0.0.0:8000 'app:create_app()' --access-logfile ./log/gunicorn-access.log --error-logfile ./log/gunicorn-error.log --capture-output ./log/gunicorn-output.log --log-level debug 