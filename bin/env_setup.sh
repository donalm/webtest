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
export APPNAME="$(basename $project_directory)"
echo $APPNAME

export PYTHONPATH="$project_directory/lib/python2.7/site-packages${PYTHONPATH:+:$PYTHONPATH}"
echo $PYTHONPATH
