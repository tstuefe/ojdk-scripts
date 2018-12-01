# !/usr/bin/env python3


import pathlib
import sys
import argparse
import subprocess

# build one or more

# run_builds [options] all|default|release+fastdebug+slowdebug+nopch+zero
# [options]  -c codeline
#            -i incremental build

ojdk_root = '/shared/projects/openjdk'
target = 'images'
variants_to_build = None;

# define codelines and their attributes
codelines_and_attributes = (
    # [ <codeline name>, <boot jdk to use>, <needs hgforest> ]
    ( 'jdk-jdk',        'openjdk11',        False ), # jdk12
    ( 'jdk-submit',     'openjdk11',        False ), # jdk12
    ( 'jdk-jdk11u',     'openjdk10',        False ),
    ( 'jdk-jdk8u',      'openjdk8',         True )
)

def valid_codelines:
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

def valid_build_variants:
    result = []
    for x in build_variants_and_attributes:
        result.append(x[0])
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

parser = argparse.ArgumentParser(
    description='Runs a sequence of OpenJDK builds.'
)

valid_codelines = valid_codelines()
default_codeline = valid_codelines[0]

parser.add_argument("-c", "--codeline", default=default_codeline,
                    help="Codeline (repository) to build. Default: %(default)s.",
                    choices=valid_codelines)

parser.add_argument("-v", "--verbose", dest="is_verbose",
                    help="Debug output", action="store_true")

parser.add_argument("-m", "--mode",
                    choices=["full", "incremental"], default="full",
                    help="Mode: full - runs a full build (configure + clean + build). "
                         "incremental - runs an incremental build, avoiding configure + clean."
                         "Default: %(default)s."
                    )

parser.add_argument("--pull",
                    help="Pull changes from upstream first before building. Fails if there are uncommitted changes in the"
                         "workspace or local changes applied (specify --qpop to pop local mq changes)", action="store_true"
                    )

parser.add_argument("--qpop",
                    help="Pop mq changes before building. Will fail if there are uncommitted changes in the workspace.",
                    action="store_true"
                    )

parser.add_argument("-t", "--target", default="images",
                    help="Overwrite the build target name(s). By default, \"images\" is built.",
                    action="store_true")

parser.add_argument("--openjdk-root", dest="ojdk_root", default=ojdk_root,
                    help="Openjdk base directory. Serves as base directory for other paths. Default: %(default)s.")


args = parser.parse_args()
if args.is_verbose:
    trc(str(args))

ojdk_root = args.ojdk_root

target = "images"
if args.target is not None:
    target = args.target

# ---






# sanity: -n,-d makes only sense in webrev mode
if args.patch_mode:
    if args.overwrite_last_webrev:
        sys.exit("Option -o|--overwrite-last-webrev only supported in webrev mode.")
    if args.delta_mode:
        sys.exit("Option -d|--delta only supported in webrev mode.")

# check that all changes are qrefresh'ed
if run_command_and_return_stdout(['hg', 'diff']) != '':
    sys.exit('There are open changes in the workspace. Please commit/qrefresh first.')
else:
    verbose('No outstanding changes in workspace - OK.')

# Now find out the outgoing changes and put them into a list:
# [(revision, description), (revision, description), ...]
outgoing_changes = get_outgoing_changes()
if len(outgoing_changes) == 0:
    sys.exit("Found no outgoing changes. Not sure what you want from me?")
else:
    trc("Found {0} outgoing changes - oldest to youngest (tip):.".format(len(outgoing_changes)))
    print(outgoing_changes)

# Patch-Mode, Webrev-Mode: need 1 outgoing changes.
# Delta-Webrev-Mode: need 2 outgoing changes.
if args.patch_mode:
    if len(outgoing_changes) != 1:
        sys.exit('We expect exactly one outgoing change in patch mode.')
else:
    if not args.delta_mode:
        if len(outgoing_changes) != 1:
            sys.exit('We expect exactly one outgoing change in webrev mode.')
    else:
        if len(outgoing_changes) != 2:
            sys.exit('We expect exactly two outgoing changes for delta webrev mode.')

# name of patch is generated from the first line of the mercurial change description of the outgoing change. In delta
# mode, from the first line of the mercurial change description of the base change.
# However, with option --patch-name the name can be overwritten from the command line.
patch_name = args.patch_name
if patch_name is None:
    patch_name = outgoing_changes[0][1]
# Sanitize patch name
patch_name = sanitize_patch_name(patch_name)
trc("Patch name is " + patch_name)

patch_directory = export_dir + '/' + patch_name
pathlib.Path(patch_directory).mkdir(parents=True, exist_ok=True)

if args.patch_mode:

    # patch mode:
    # Produce new patch with hg export. Delete any pre-existing patches but ask
    # user first.
    patch_file_path = patch_directory + '/' + patch_name + '.patch'
    if pathlib.Path(patch_file_path).exists():
        user_confirm('Remove pre-existing patch: ' + patch_file_path)
        pathlib.Path(patch_file_path).unlink()
        trc("Removed pre-existing patch at " + patch_file_path + ".")
    run_command_and_return_stdout(["hg", "export", "-o", patch_file_path])
    trc("Created new patch at " + patch_file_path + " - OK.")

else:

    # webrev mode:
    # First, find existing highest-numbered webrev directory for this change
    # ( export/<patch name>/webrev_<iteration>)
    webrev_number_first_invalid = 0
    webrev_number_last_valid = -1
    while pathlib.Path(build_webrev_path(patch_directory, webrev_number_first_invalid)).exists():
        webrev_number_last_valid = webrev_number_first_invalid
        webrev_number_first_invalid += 1

    webrev_number = -1
    if args.overwrite_last_webrev and webrev_number_last_valid >= 0:
        webrev_number = webrev_number_last_valid
    else:
        webrev_number = webrev_number_first_invalid

    webrev_dir_path = build_webrev_path(patch_directory, webrev_number)
    delta_webrev_dir_path = build_delta_webrev_path(patch_directory, webrev_number)

    # ask before overwriting
    if pathlib.Path(webrev_dir_path).exists():
        user_confirm('Remove pre-existing webrev directory: ' + webrev_dir_path)
        remove_directory(webrev_dir_path)
        # ... and also remove old webrev delta, should it exist
        # (we do not ask again, just do it)
        if pathlib.Path(delta_webrev_dir_path).exists():
            remove_directory(delta_webrev_dir_path)

    # Now create the new webrev:
    if not args.delta_mode:
        # In normal (non-delta) mode, we just run webrev.ksh without specifying any revision
        run_command_and_return_stdout(["ksh", webrev_script_location, "-o", webrev_dir_path])
        trc("Created new webrev at " + webrev_dir_path + " - OK.")
    else:
        # In delta mode, we create two webrevs, one for the delta part, one for the full part.

        # Delta part: use -r <rev> where revision is the parent, which in this case is the base part.
        run_command_and_return_stdout(["ksh", webrev_script_location, "-o", delta_webrev_dir_path, "-r",
                                       str(outgoing_changes[0][0])])
        trc("Created new delta webrev at " + delta_webrev_dir_path + " - OK.")

        # Full part: just run webrev normally without specifying a revision. It will pick up all outgoing changes,
        # which are two (base + delta)
        run_command_and_return_stdout(["ksh", webrev_script_location, "-o", webrev_dir_path])
        trc("Created full webrev (base + delta) at " + webrev_dir_path + " - OK.")

# upload to remote: For simplicity, I just transfer the whole patch dir, regardless if that transfers
# older webrevs too. rsync will only transfer stuff not remote already.
if args.upload:
    trc("Uploading patch...")
    source = patch_directory
    result = run_command_and_return_stdout(["rsync", "-avz", "-e", "ssh", source, upload_url])
    trc("Did upload " + patch_directory + " to " + upload_url + " - OK.")
