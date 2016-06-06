#!/usr/bin/zsh

if [ -e $VIRTUAL_ENV ]; then
    export PATH=${VIRTUAL_ENV}/bin:${PATH}
fi

bin_directory=$(cd -P -- "$(dirname -- "$0")" && printf '%s\n' "$(pwd -P)")
source "$bin_directory/env_setup.sh"

txwebtest_username="txwebtest"
txwebtest_groupname="txwebtest"

if [ -z $WEBTEST_INSTANCE ]; then
    export WEBTEST_INSTANCE="001"
fi

getent passwd $txwebtest_username > /dev/null
if [ $? -eq 0 ]; then
    # Ok - user exists
else
    echo "ERROR: LINUX USER '$txwebtest_username' DOES NOT EXIST"
    echo "PLEASE RUN THE create_user.sh SCRIPT FROM THIS DIRECTORY"
    exit 1
fi

getent group $txwebtest_groupname > /dev/null
if [ $? -eq 0 ]; then
    # Ok - group exists
else
    echo "ERROR: LINUX GROUP '$txwebtest_groupname' DOES NOT EXIST"
    echo "PLEASE RUN THE create_user.sh SCRIPT FROM THIS DIRECTORY"
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

pidfile="${pidfile_directory}/${APPNAME}.$WEBTEST_INSTANCE.pid"

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

    while [[ "$INTERPRETER" = "$(ps -hp $pid -o comm=)" ]]; do
        echo "WAITING FOR PID $pid"
        sleep 1
    done

fi;

interpreter=`which $INTERPRETER`
if [ $? -eq 0 ]; then
    # Ok - $INTERPRETER is in PATH
else
    echo "COULD NOT FIND $INTERPRETER"
    exit 1
fi


twistd=`which twistd`
if [ $? -eq 0 ]; then
    # Ok - twistd is in PATH
else
    echo "COULD NOT FIND twistd"
    exit 1
fi


if [ "$STARTUP" = "1" ]; then
    echo "STARTUP COMMAND:" $interpreter $twistd --uid=$txwebtest_uid --gid=$txwebtest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
    exec $interpreter $twistd --uid=$txwebtest_uid --gid=$txwebtest_gid --pidfile=${pidfile} -y $project_directory/tac/web.tac
fi;
