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


def codeline_root():
    return ojdk_root + '/' + args.codeline


def output_dir_for_variant(variant):
    return codeline_root() + '/output-' + variant


def source_dir():
    return codeline_root() + '/source'


# define codelines and their attributes
codelines_and_attributes = (
    # [ <codeline name>, <boot jdk to use>, <needs hgforest> ]
    ('jdk-jdk', 'openjdk11', False),  # jdk12
    ('jdk-submit', 'openjdk11', False),  # jdk12
    ('jdk-jdk11u', 'openjdk10', False),
    ('jdk-jdk8u', 'openjdk8', True)
)


def valid_codelines():
    result = []
    for x in codelines_and_attributes:
        result.append(x[0])
    return result


def codeline_data_by_name(name: str) -> list:
    for x in codelines_and_attributes:
        if x[0] == name:
            return x
    return None


# define build variants and their attributes
build_variants_and_attributes = (
    # <name>, <configure options>
    ('slowdebug', '--with-debug-level=slowdebug'),
    ('fastdebug', '--with-debug-level=fastdebug'),
    ('fastdebug-nopch', '--with-debug-level=fastdebug --disable-precompiled-headers'),
    ('fastdebug-zero', '--with-debug-level=fastdebug --with-jvm-variants=zero'),
    ('release', '--with-debug-level=release'),
)


def valid_build_variants() -> tuple:
    result = []
    for x in build_variants_and_attributes:
        result.append(x[0])
    return result


def variant_data_by_name(name: str) -> list:
    for x in build_variants_and_attributes:
        if x[0] == name:
            return x
    return None


# a build variant combination is a set of build variants, with a shorthand moniker
build_variant_combos = (
    # name, [ array of build variants ]
    ('some', ['fastdebug', 'release']),
    ('all', valid_build_variants())
)


def valid_build_variant_combos():
    result = []
    for x in build_variant_combos:
        result.append(x[0])
    return result


# function takes a name of a build variant combos and returns a list of its build variants
def resolve_build_variant_combo(combo_name):
    result = []
    for x in build_variant_combos:
        if x[0] == combo_name:
            result.extend(x[1])
            break
    verbose("Resolving combo: " + combo_name + "->" + str(result))
    return result


# given a list of build variant names which may contain combos, return an array with all combos replaced
# by their content
def resolve_combos_in_list(unresolved_list):
    result = []
    for x in unresolved_list:
        unrolled = resolve_build_variant_combo(x)
        if len(unrolled) > 0:
            result.extend(unrolled)
        else:
            result.append(x)
    return result


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


def are_there_outgoing_changes_in_repo():
    outgoing_changes = run_command_and_return_stdout(['hg', 'out', '-q'])
    return len(outgoing_changes) > 0


def are_there_uncommitted_changes_in_workspace():
    uncommitted_changes = run_command_and_return_stdout(['hg', 'diff'])
    return len(uncommitted_changes) > 0


# run one build for the given variant and the given mode (see --mode)
def run_build_for_variant(codeline, variant_name, mode):
    verbose("Building: codeline " + codeline + ", variant: " + variant_name + ", mode: " + mode)

    codeline_data = codeline_data_by_name(codeline)
    boot_jdk = codeline_data[1]

    variant_data = variant_data_by_name(variant_name)
    configure_options = variant_data[1].split()

    configure_options.append("--with-boot-jdk=" + ojdk_root + "/jdks/" + boot_jdk)

    # add release jdk as build jdk if this is any variant other than release
    if variant_name != "release":
        configure_options.append("--with-build-jdk=" + output_dir_for_variant("release") + "/images/jdk")

    verbose("Configure options: " + str(configure_options))

    # create output dir
    output_dir = output_dir_for_variant(variant_name)
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    verbose("Output dir: " + output_dir)

    os.chdir(output_dir)

    # run configure
    if mode == "configure-only" or mode == "full":
        command = ["bash", "../source/configure"] + configure_options
        if args.dry_run:
            verbose("(Dry run): " + str(command))
        else:
            run_command_and_return_stdout(command)

    # clean
    if mode == "full":
        command = ["make", "clean"]
        if args.dry_run:
            verbose("(Dry run): " + str(command))
        else:
            run_command_and_return_stdout(["make", "clean"])

    if mode == "full" or mode == "incremental":
        targets = args.target.split()
        command = ["make"] + targets
        if args.dry_run:
            verbose("(Dry run): " + str(command))
        else:
            run_command_and_return_stdout(command)


# End: def run_build_for_variant(variant_name, mode):


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
                    choices=["full", "incremental", "configure-only"], default="full",
                    help="Mode: full - runs a full build (configure + clean + build). "
                         "incremental - runs an incremental build, avoiding configure + clean."
                         "configure-only - runs only configure. "
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

parser.add_argument("--dry-run", dest="dry_run", default=False, action="store_true",
                    help="Do not do anything, just act as if you did.")

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

####################################
# resolve build variant combos ("some", "all")

variants_to_build = resolve_combos_in_list(args.build_variants)

trc("Building: " + args.codeline + ", variants: " + str(variants_to_build))

####################################
# Sanity

if not pathlib.Path(ojdk_root).exists():
    sys.exit('Cannot find openjdk root directory at ' + ojdk_root + '.');

if not pathlib.Path(source_dir()).exists():
    sys.exit('Cannot find source directory at ' + source_dir() + '.')

#####################################
# Preparation:

curdir = os.getcwd()

# in pull mode, we expect the workspace to be empty and no outgoing changes to be present
if args.pull:

    os.chdir(source_dir())
    trc("--pull specified: attempting to pull new changes...")

    # we should have no uncommitted changes.
    if are_there_uncommitted_changes_in_workspace():
        sys.exit('There are uncommitted changes in the workspace. Please commit/qrefresh your changes and try again.')
    else:
        verbose("No uncommitted changes found... OK.")

    # outgoing changes we either autopop (and assume they are mercurial changes), or abort
    if are_there_outgoing_changes_in_repo():
        if args.qpop:
            trc("Found outgoing changes. Attempting to qpop them...")
            run_command_and_return_stdout(["hg", "qpop", "-a"])
            if are_there_outgoing_changes_in_repo():
                sys.exit('Failed to qpop outgoing changes. Are these mq changes? Please manually correct and retry.')
        else:
            sys.exit('Found outgoing changes. Please remove or qpop or whatever, then retry.')

    # now pull:
    pulled = run_command_and_return_stdout(["hg", "pull", "-u"])
    trc(pulled)
    trc("Pulled changes. Ok.")

    os.chdir(curdir)

# Now build.

have_built_release_already = False

for this_variant_name in variants_to_build:
    verbose("Variant: " + this_variant_name)
    if this_variant_name != "release":
        if not have_built_release_already:
            verbose("Need a release jkd to be used as build jdk...")
            # we need a full release jdk even to run configure for any other variant since the configure script checks
            # the jdk. Build one if there is none already; if there is, we assume it is still good.
            if not pathlib.Path(output_dir_for_variant("release") + "/images/jdk/bin/java").exists():
                verbose("Lets build that first.")
                run_build_for_variant(args.codeline, "release", "full")
            else:
                verbose("Not needed, found one.")

            variants_to_build.remove("release")
            have_built_release_already = True

    # build this variant
    run_build_for_variant(args.codeline, this_variant_name, args.mode)
    if this_variant_name == "release":
        have_built_release_already = True


