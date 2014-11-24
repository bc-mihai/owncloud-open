#!/bin/sh

curdir=$(dirname $0)
uri=$($curdir/owncloud_transform.py "$1")

echo "$uri" | xclip -selection clipboard
echo "$uri" | xclip

if [ $? = 0 ]; then
    notify-send "Copied to clipboard" "$uri"
else
    notify-send -i error "Could not copy to clipboard" "Please install xclip!"
fi
