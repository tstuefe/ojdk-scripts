#! /usr/bin/env bash

set -e

# scans the build log and outputs, for the hotspot build, the list of cpp files compiled 
# and their compile options

USAGE="$0 <path-to-build-log>"

if [ -z "$1" ]; then
    echo $USAGE
    exit -1
fi

BUILD_LOG="$1"

if [ ! -f "$BUILD_LOG" ]; then
    echo "Cannot find build log at ${BUILD_LOG}."
    exit -1
fi

echo "List of compiled C++ Files:"

egrep -o 'src\/hotspot\/[[:alnum:]_\/]*\.cpp' "$BUILD_LOG" | sort | uniq

echo 

compile_line=$(egrep -o '\/usr\/bin\/g++.*\/os.cpp' "$BUILD_LOG")

echo "List of Includes:"

for token in $compile_line; do
    if [[ "$token" = -I* ]]; then
        echo $token
    fi
done

echo 

echo "List of Defines:"

for token in $compile_line; do
    if [[ "$token" = -D* ]]; then
        echo $token
    fi
done

