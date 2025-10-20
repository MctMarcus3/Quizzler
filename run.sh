#!/bin/sh
# This script starts the Gunicorn production server.
gunicorn --workers 4 --bind 0.0.0.0:8000 'app:app'