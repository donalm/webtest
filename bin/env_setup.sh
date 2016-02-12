#!/usr/bin/zsh
################################################
#
# Environment setup for zsh
#
# This script makes the assumption that we're in the bin directory, immediately
# underneath the project directory. The name of the project directory must be 
# the name of the project, so for example if our project is called "rumblefish"
# then this would work:
#
# /home/francis/code/rumblefish/bin/env_setup.sh
#
################################################


bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
project_directory="$(dirname $bin_directory)"
echo $project_directory
base_directory="$(dirname $project_directory)"
echo $base_directory
export APPNAME="$(basename $project_directory)"
eval "export ${APPNAME:u}_PROJECT_DIRECTORY=${project_directory}"
export PYTHONPATH="$project_directory/lib/python${PYTHONPATH:+:$PYTHONPATH}"
