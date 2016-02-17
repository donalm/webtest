#!/usr/bin/zsh

bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/env_setup.sh"

cd $project_directory/lib/python/webtest

/usr/local/bin/trial webtest.test.test_session
