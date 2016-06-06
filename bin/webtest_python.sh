#!/usr/bin/zsh

export INTERPRETER=python
bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/webtest.sh"
