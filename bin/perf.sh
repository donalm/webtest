#!/usr/bin/zsh

bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/env_setup.sh"

txperftest_username="txperftest"
txperftest_groupname="txperftest"

if [ -z $WEBTEST_INSTANCE ]; then
    export WEBTEST_INSTANCE="001"
fi

getent passwd $txperftest_username > /dev/null
if [ $? -eq 0 ]; then
    # Ok - user exists
else
    echo "ERROR: USER $txperftest_username DOES NOT EXIST"
    exit 1
fi

if [ "$USER" != "$txperftest_username" ] && [ "$USER" != "root" ]
then
    echo "ERROR: This process can only be managed by $txperftest_username or root. Not ${USER}";
    exit 1;
fi

tmp_directory="/tmp/${APPNAME}"
if [ -d $tmp_directory ]
then
    # OK - Let's hope we have write-access
else
    mkdir -p $tmp_directory
    chown $txperftest_username:$txperftest_groupname $tmp_directory
    chmod 750 $tmp_directory
fi

cd $tmp_directory

pidfile_directory="/var/run/${APPNAME}"
if [ "$USER" = "root" ]; then

    log_directory="/var/log/${APPNAME}"
    mkdir -p $log_directory
    chown $txperftest_username:$txperftest_username $log_directory
    chmod 750 $log_directory

    mkdir -p $pidfile_directory
    chown $txperftest_username:$txperftest_username $pidfile_directory
    chmod 750 $pidfile_directory
fi

pidfile="${pidfile_directory}/${APPNAME}.$WEBTEST_INSTANCE.pid"

txperftest_uid="$(/usr/bin/id -u $txperftest_username)"
txperftest_gid="$(/usr/bin/getent group $txperftest_groupname | /usr/bin/cut -d: -f3)"

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
    echo "STARTUP COMMAND:" /usr/bin/pypy /usr/local/bin/twistd --uid=$txperftest_uid --gid=$txperftest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
    exec /usr/bin/pypy /usr/local/bin/twistd --uid=$txperftest_uid --gid=$txperftest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
fi;
