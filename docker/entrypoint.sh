#!/bin/sh
set -e

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  python backend/manage.py migrate --noinput
fi


if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
  python backend/manage.py collectstatic --noinput
fi

exec "$@"
