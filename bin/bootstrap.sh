#!/usr/bin/zsh

bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/env_setup.sh"

echo $PYTHONPATH

exec "$0.py" "$@"
