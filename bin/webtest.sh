#!/usr/bin/zsh

export INTERPRETER=pypy
bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/_webtest.sh"
