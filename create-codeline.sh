#! /usr/bin/env bash
set -e
set -u

USAGE="Usage: $0 <repo-name>"
OPENJDK_SOURCE_ROOT="/shared/projects/openjdk"
REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "$USAGE"
    exit -1
fi

function create_directory_if_it_does_not_exists_yet {
    echo "Creating $1..."
    if [ -d "$1" ]; then
        echo "Skipping."
    else
        mkdir "$1"
        echo "Done."
    fi
}

cd "$OPENJDK_SOURCE_ROOT"
create_directory_if_it_does_not_exists_yet "$REPO_NAME"
cd "$REPO_NAME"

create_directory_if_it_does_not_exists_yet "source"

create_directory_if_it_does_not_exists_yet "output-release"

create_directory_if_it_does_not_exists_yet "output-fastdebug"

create_directory_if_it_does_not_exists_yet "output-fastdebug-nopch"

create_directory_if_it_does_not_exists_yet "output-fastdebug-zero"

create_directory_if_it_does_not_exists_yet "output-slowdebug"

if [ ! -d "source/.hg" ]; then
    wget "https://builds.shipilev.net/workspaces/${REPO_NAME}.tar.xz"
    tar -xf "${REPO_NAME}.tar.xz"
    rm -r "source"
    mv "$REPO_NAME" source
    cd source
    hg up
    hg pull -u
    cd ..
else
    echo "Found source. Skipping clone."
fi



CDT_WS_DIR="cdt-ws-${REPO_NAME}"
if [ ! -d $CDT_WS_DIR ]; then
    mkdir $CDT_WS_DIR
    cd $CDT_WS_DIR
    git clone https://github.com/tstuefe/ojdk-cdt.git
    cd ..
fi




