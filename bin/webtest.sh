#!/usr/bin/zsh

bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/env_setup.sh"

txwebtest_username="txwebtest"
txwebtest_groupname="txwebtest"

getent passwd $txwebtest_username > /dev/null
if [ $? -eq 0 ]; then
    # Ok - user exists
else
    echo "ERROR: USER $txwebtest_username DOES NOT EXIST"
    exit 1
fi

if [ "$USER" != "$txwebtest_username" ] && [ "$USER" != "root" ]
then
    echo "ERROR: This process can only be managed by $txwebtest_username or root. Not ${USER}";
    exit 1;
fi

tmp_directory="/tmp/${APPNAME}"
if [ -d $tmp_directory ]
then
    # OK - Let's hope we have write-access
else
    mkdir -p $tmp_directory
    chown $txwebtest_username:$txwebtest_groupname $tmp_directory
    chmod 750 $tmp_directory
fi

cd $tmp_directory

pidfile_directory="/var/run/${APPNAME}"
if [ "$USER" = "root" ]; then

    log_directory="/var/log/${APPNAME}"
    mkdir -p $log_directory
    chown $txwebtest_username:$txwebtest_username $log_directory
    chmod 750 $log_directory

    mkdir -p $pidfile_directory
    chown $txwebtest_username:$txwebtest_username $pidfile_directory
    chmod 750 $pidfile_directory
fi

pidfile="${pidfile_directory}/${APPNAME}.pid"

txwebtest_uid="$(/usr/bin/id -u $txwebtest_username)"
txwebtest_gid="$(/usr/bin/getent group $txwebtest_groupname | /usr/bin/cut -d: -f3)"

SHUTDOWN=0
STARTUP=0

if [ "$1" = "start" ]; then
    STARTUP=1
elif [ "$1" = "restart" ]; then
    STARTUP=1
    SHUTDOWN=1
elif [ "$1" = "stop" ]; then
    SHUTDOWN=1
fi;

if [ "$SHUTDOWN" = "1" ]; then

    pid=$(cat $pidfile)
    if [ "$pid" != "" ]; then
        kill $pid
    fi;

    while [[ "pypy" = "$(ps -hp $pid -o comm=)" ]]; do
        echo "WAITING FOR PID $pid"
        sleep 1
    done

fi;


if [ "$STARTUP" = "1" ]; then
    echo "STARTUP COMMAND:" /usr/bin/pypy /usr/local/bin/twistd --uid=$txwebtest_uid --gid=$txwebtest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
    exec /usr/bin/pypy /usr/local/bin/twistd --uid=$txwebtest_uid --gid=$txwebtest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
fi;
