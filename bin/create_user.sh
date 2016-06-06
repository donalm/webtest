#!/usr/bin/zsh
useradd -r -s /bin/false txwebtest
usermod -a -G redis txwebtest

if [ "$USER" = "root" ]; then
    user=$SUDO_USER
else
    user=$USER
fi

if [ -n "$user" ]; then
	usermod -a -G txwebtest $user
fi
