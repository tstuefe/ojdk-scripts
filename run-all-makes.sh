#! /usr/bin/env bash
set -e


USAGE="Usage: $0 <repo-name> [(all|some|none)]"
OPENJDK_SOURCE_ROOT="/shared/projects/openjdk"
REPO_NAME="$1"
BUILD_WHAT="$2"

if [ -z "$REPO_NAME" ]; then
    echo "$USAGE"
    exit -1
fi

# decide which builds (if any) to run
DO_BUILD_RELEASE=0
DO_BUILD_FASTDEBUG=0
DO_BUILD_FASTDEBUG_NOPCH=0
DO_BUILD_FASTDEBUG_ZERO=0
DO_BUILD_SLOWDEBUG=0

if [ -z "$BUILD_WHAT" ]; then
    BUILD_WHAT="some"
fi

if [ "$BUILD_WHAT" == "none" ]; then
    echo "Only running configures..."
elif [ "$BUILD_WHAT" == "some" ]; then
    echo "Building important jdks"
    DO_BUILD_RELEASE=1
    DO_BUILD_FASTDEBUG=1
elif [ "$BUILD_WHAT" == "all" ]; then
    echo "Building all jdks"
    DO_BUILD_RELEASE=1
    DO_BUILD_FASTDEBUG=1
    DO_BUILD_FASTDEBUG_NOPCH=1
    DO_BUILD_FASTDEBUG_ZERO=1
    DO_BUILD_SLOWDEBUG=1
else
    echo "Invalid option for -build"
fi

# usage: run_configure_and_make <output-dir> <full make? 1|0> <additional configure options>
function run_configure_and_possibly_make {
    cd "$1"
    set +e
    bash ../source/configure --with-boot-jdk=../../jdks/openjdk10 $3 $4 $5 > "/tmp/build-${REPO_NAME}-$1.log" 2>&1
    if [ "$2" == "1" ]; then
        echo "Running full make for $1..."
        make clean images LOG=debug >> "/tmp/build-${REPO_NAME}-$1.log" 2>&1
    fi
    if [ "$?" == 0 ]; then
        BUILD_RESULT="OK"
    else
        BUILD_RESULT="ERROR"
    fi
    set -e
    cd ..
}

cd "$OPENJDK_SOURCE_ROOT/$REPO_NAME"

# update source
#pushd source
#set +e
#hg qpop
#set -e
#hg up -C
#popd

WITH_BUILD_JDK="--with-build-jdk=../output-release/images/jdk"
DISABLE_PCH="--disable-precompiled-headers"
ZERO="--with-jvm-variants=zero"

BUILD_RESULT="???"

run_configure_and_possibly_make output-release "$DO_BUILD_RELEASE" \
--with-debug-level=release
echo "release: ${BUILD_RESULT}"

BUILD_RESULT="???"
run_configure_and_possibly_make output-fastdebug "$DO_BUILD_FASTDEBUG" \
--with-debug-level=fastdebug $WITH_BUILD_JDK
echo "fastdebug: ${BUILD_RESULT}"

BUILD_RESULT="???"
run_configure_and_possibly_make output-fastdebug-nopch "$DO_BUILD_FASTDEBUG_NOPCH" \
--with-debug-level=fastdebug $WITH_BUILD_JDK $DISABLE_PCH
echo "fastdebug-nopch: ${BUILD_RESULT}"

BUILD_RESULT="???"
run_configure_and_possibly_make output-fastdebug-zero "$DO_BUILD_FASTDEBUG_ZERO" \
--with-debug-level=fastdebug $WITH_BUILD_JDK $ZERO
echo "fastdebug-zero: ${BUILD_RESULT}"

BUILD_RESULT="???"
run_configure_and_possibly_make output-slowdebug "$DO_BUILD_SLOWDEBUG" \
--with-debug-level=slowdebug $WITH_BUILD_JDK
echo "slowdebug: ${BUILD_RESULT}"


