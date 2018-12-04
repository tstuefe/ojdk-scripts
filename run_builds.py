# !/usr/bin/env python3


import pathlib
import sys
import os
import argparse
import subprocess

# build one or more

# run_builds [options] all|default|release+fastdebug+slowdebug+nopch+zero
# [options]  -c codeline
#            -i incremental build

ojdk_root = '/shared/projects/openjdk'

# define codelines and their attributes
codelines_and_attributes = (
    # [ <codeline name>, <boot jdk to use>, <needs hgforest> ]
    ( 'jdk-jdk',        'openjdk11',        False ), # jdk12
    ( 'jdk-submit',     'openjdk11',        False ), # jdk12
    ( 'jdk-jdk11u',     'openjdk10',        False ),
    ( 'jdk-jdk8u',      'openjdk8',         True )
)

def valid_codelines():
    result = []
    for x in codelines_and_attributes:
        result.append(x[0])
    return result

# define build variants and their attributes
build_variants_and_attributes = (
    # <name>, <needs release as build jdk>, <configure options>
    ( 'release', False, '--with-debug-level=release' ),
    ( 'slowdebug', True, '--with-debug-level=slowdebug' ),
    ( 'fastdebug', True, '--with-debug-level=fastdebug' ),
    ( 'fastdebug-nopch', True, '--with-debug-level=fastdebug --disable-precompiled-headers' ),
    ( 'fastdebug-zero', True, '--with-debug-level=fastdebug --with-jvm-variants=zero' ),
)

def valid_build_variants() -> tuple:
    result = []
    for x in build_variants_and_attributes:
        result.append(x[0])
    return result


def variant_by_name(name: str) -> list:
    for x in build_variants_and_attributes:
        if x[0] == name:
            return x
    return None


# a build variant combination is a set of build variants, with a shorthand moniker
build_variant_combos = (
    # name, [ array of build variants ]
    ( 'some',       ('fastdebug', 'release') ),
    ( 'all',        valid_build_variants() )
)

def valid_build_variant_combos():
    result = []
    for x in build_variant_combos:
        result.append(x[0])
    return result

# function takes a name of a build variant combos and returns a list of its build variants
def unroll_build_variant_combo(name):
    result = []
    for x in build_variant_combos:
        if x[0] == name:
            result.append(x[1])
    return result

# given a list of build variant names which may contain combos, return an array with all combos replaced
# by their content
def unroll_all_build_variant_combos_in_list(list):
    result = []
    for x in list:
        unrolled = unroll_build_variant_combo(x)
        if len(unrolled) > 0:
            result = result + unrolled
        else:
            result = result + x
    return result


def output_dir_for_variant(variant):
    return ojdk_root + '/output-' + variant

def trc(text):
    print("--- " + text)

def verbose(text):
    if args.is_verbose:
        print("--- " + text)

def run_command_and_return_stdout(command):
    verbose('calling: ' + ' '.join(command))
    try:
        stdout = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        trc('Command failed ' + ' '.join(command))
        print(e)
        sys.exit('Sorry :-(')
    stdout = stdout.decode("utf-8")
    verbose('out: ' + stdout)
    return stdout

# Returns a list of [(int, str)] tuples containing the local revision number and description, respectively,
# of all outgoing changes. First one in the list is the oldest change, last one the youngest (tip).
def get_outgoing_changes() -> list:
    # Note: print revision number and first line of patch description. The latter is used as base for the
    # patch name unless a patch name is given via --patch-name.
    s = run_command_and_return_stdout(["hg", "outgoing", "-q", "-T", "{rev}###{desc|firstline|lower}\n"])
    lines = s.splitlines()
    return_list = []
    for line in lines:
        list_entry = line.split('###')

        revision_number = int(list_entry[0])
        description = list_entry[1]

        list_entry_tuple = (revision_number, description)
        return_list.append(list_entry_tuple)
    return return_list

def check_for_outgoing_changes():
    outgoing = get_outgoing_changes()
    if len(outgoing) > 0:
        sys.exit('There are uncommitted changes in the workspace. Please commit/qrefresh first.')

def check_for_uncommitted_changes_in_workspace():
    if run_command_and_return_stdout(['hg', 'diff']) != '':
        sys.exit('There are open changes in the workspace. Please commit/qrefresh first.')
    else:
        verbose('No outstanding changes in workspace - OK.')


def run_one_build(variant_name):
    variant = variant_by_name(variant_name)
    if variant == None:
        sys.exit("Invalid variant? " + variant_name)

    # Does this need a release build?
    if variant[1]





parser = argparse.ArgumentParser(
    description='Runs a sequence of OpenJDK builds.'
)

valid_codelines = valid_codelines()
default_codeline = valid_codelines[0]

parser.add_argument("-c", "--codeline", default=default_codeline, metavar="CODELINE",
                    help="Codeline (repository) to build. Default: %(default)s. Valid values: %(choices)s.",
                    choices=valid_codelines)

parser.add_argument("-v", "--verbose", dest="is_verbose", default=False,
                    help="Debug output", action="store_true")

parser.add_argument("-m", "--mode",
                    choices=["full", "incremental"], default="full",
                    help="Mode: full - runs a full build (configure + clean + build). "
                         "incremental - runs an incremental build, avoiding configure + clean."
                         "Default: %(default)s.")

parser.add_argument("--pull", default=False,
                    help="Pull changes from upstream first before building. Fails if there are uncommitted changes in "
                         "workspace or local changes applied (use --qpop to pop local mq changes)", action="store_true")

parser.add_argument("--qpop", default=False,
                    help="Pop mq changes before building. Will fail if there are uncommitted changes in the workspace.",
                    action="store_true")

parser.add_argument("-t", "--target", default="images",
                    help="Overwrite the build target name(s). By default, \"images\" is built.",
                    action="store_true")

parser.add_argument("--openjdk-root", dest="ojdk_root", default=ojdk_root,
                    help="Openjdk base directory. Serves as base directory for other paths. Default: %(default)s.")

# positional args


parser.add_argument("build_variants", default=build_variant_combos[0][1], nargs='+', metavar="BUILD-VARIANT",
                    choices=valid_build_variants() + valid_build_variant_combos(),
                    help="Variant(s) to build. Default: %(default)s. "
                    "Valid values: %(choices)s.")



args = parser.parse_args()
if args.is_verbose:
    trc(str(args))

# unroll build variants
variants_to_build = unroll_all_build_variant_combos_in_list(args.build_variants)


verbose("variants_to_build: " + variants_to_build)

####################################
# Sanity

if not pathlib.Path(ojdk_root).exists():
    sys.exit('Cannot find openjdk root directory at ' + ojdk_root + '.');

source_root = ojdk_root + "/" + args.codeline + "/source"

if not pathlib.Path(source_root).exists():
    sys.exit('Cannot find source directory at ' + source_root + '.');


#####################################
# Preparation:

# in pull mode, we expect the workspace to be empty and no outgoing changes to be present
if args.pull:

    os.chdir(source_root)

    trc("Attempting to pull new changes.")

    # we should have no uncommitted changes.
    trc("Check for uncommitted changes in the workspace...")
    check_for_uncommitted_changes_in_workspace()
    trc("OK.")

    # if qpop is given, use qpop to remove outgoing changes, otherwise exit
    if args.qpop:
        trc("Attempting to pop all outgoing changes...")
        run_command_and_return_stdout(["hg", "qpop", "-a"])

    # by now we should have no outgoing changes.
    trc("Check for outgoing changes...")
    check_for_outgoing_changes()
    trc("OK.")

    # now pull:
    run_command_and_return_stdout(["hg", "pull", "-u"])
    trc("OK.")










