#!/usr/bin/env bash
set -e

# this if will check if the first argument is a flag
# but only works if all arguments require a hyphenated flag
# -v; -SL; -f arg; etc will work, but not arg1 arg2
if [ "${1:0:1}" = '-' ]; then
    set -- crond "$@"
fi

# check if running crond
if [ "$1" = 'crond' ]; then
  exec crond "$@"
fi

# else default to run whatever the user wanted like "bash"
exec "$@"
