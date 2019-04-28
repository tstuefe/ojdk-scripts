#! /usr/bin/env bash
set -e
set -u

USAGE="Usage: $0 <repo-name>"
OPENJDK_ROOT="/shared/projects/openjdk"
REPO_NAME="$1"

if [ -z "$REPO_NAME" ]; then
    echo "$USAGE"
    exit -1
fi

REPO_ROOT="${OPENJDK_ROOT}/${REPO_NAME}"

function create_directory_if_it_does_not_exists_yet {
    echo "Creating $1..."
    if [ -d "$1" ]; then
        echo "Skipping."
    else
        mkdir "$1"
        echo "Done."
    fi
}

create_directory_if_it_does_not_exists_yet "$REPO_ROOT"
cd "${REPO_ROOT}"

create_directory_if_it_does_not_exists_yet "output-release"

create_directory_if_it_does_not_exists_yet "output-fastdebug"

create_directory_if_it_does_not_exists_yet "output-fastdebug-nopch"

create_directory_if_it_does_not_exists_yet "output-fastdebug-zero"

create_directory_if_it_does_not_exists_yet "output-slowdebug"

if [[ ${REPO_NAME} == sapmachine* ]]; then
    git clone git@github.com:SAP/SapMachine.git
    mv SapMachine source
    cd source
    case ${REPO_NAME} in
    "sapmachine-head")
    ;;
    "sapmachine-11") git checkout sapmachine11
    ;;
    "sapmachine-12") git checkout sapmachine12
    ;;
    esac
else
    set -e
    wget "https://builds.shipilev.net/workspaces/${REPO_NAME}.tar.xz"
    set +e
    if [ -f ${REPO_NAME}.tar.xz ]; then
        tar -xf "${REPO_NAME}.tar.xz"
        mv "$REPO_NAME" source
        cd source
        hg up
        hg pull -u
    else
        IS_FOREST=no
        case ${REPO_NAME} in
        "jdk-jdk") URL="http://hg.openjdk.java.net/jdk/jdk"
        ;;
        "jdk-submit") URL="http://hg.openjdk.java.net/jdk/submit"
        ;; 
        "jdk-sandbox") URL="http://hg.openjdk.java.net/jdk/sandbox"
        ;; 
        "jdk-sandbox") URL="http://hg.openjdk.java.net/jdk/sandbox"
        ;; 
        "jdk-jdk8u-dev") URL="http://hg.openjdk.java.net/jdk8u/jdk8u-dev"
        IS_FOREST=yes
        ;;
        "jdk-jdk11u-dev") URL="http://hg.openjdk.java.net/jdk-updates/jdk11u-dev"
        ;;
        esac
        hg clone "$URL"
        # todo: rename dir to source
    fi
fi

cd "${REPO_ROOT}"

CDT_WS_DIR="cdt-ws-${REPO_NAME}"
if [ ! -d $CDT_WS_DIR ]; then
    mkdir $CDT_WS_DIR
    cd $CDT_WS_DIR
    git clone https://github.com/tstuefe/ojdk-cdt.git
    cd ..
fi
