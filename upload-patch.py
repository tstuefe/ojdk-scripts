# !/usr/bin/env python3

# upload a patch to cr.openjdk.java.net
#
# usage: upload-patch [-p|--patch-mode] [-n|--name name] 
#


import pathlib
import sys
import argparse
import subprocess
import shutil

export_root_dir = '../../export'
export_remote_url = 'cr.openjdk.java.net'
export_remote_path = '/oj/home/stuefe/webrevs'
export_remote_user = 'stuefe'
webrev_location = '../../code-tools/webrev/webrev.ksh'


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


def user_confirm(question):
    print(question + " [y/n]: ")
    if args.yesyes:
        print("(-y: auto-yes)")
        return
    answer = None
    while answer is None:
        answer = input().lower()
        if answer == "y":
            answer = True
        elif answer == "n":
            sys.exit('No -> Cancelling.')
        else:
            print("Please respond with \'y\' or \'n\'.")
            answer = None


def build_webrev_path(patch_export_dir, webrev_number):
    return patch_export_dir + '/webrev.' + '{:02d}'.format(webrev_number)


def build_delta_webrev_path(patch_export_dir, webrev_number):
    return patch_export_dir + '/webrev_delta.' + '{:02d}'.format(webrev_number)


def remove_directory(path: str) -> str:
    shutil.rmtree(path)
    trc("Removed directory: " + path)


def remove_prefix_from_string(s: str, prefix: str) -> str:
    if s.startswith(prefix):
        s = s[len(prefix):]
    return s


# Returns a list of [(int, str)] tuples containing the local revision number and description, respectively,
# of all outgoing changes. First one in the list is the oldest change, last one the youngest (tip).
def get_outgoing_changes() -> list:
    s = run_command_and_return_stdout(["hg", "outgoing", "-q", "-T", "{rev}###{desc}\n"])
    lines = s.splitlines()
    return_list = []
    for line in lines:
        list_entry = line.split('###')

        revision_number = int(list_entry[0])
        description = list_entry[1]
        # correct patch names for some typical mq pattern:
        description = remove_prefix_from_string(description, 'imported patch ')
        description = remove_prefix_from_string(description, '[mq]: ')

        list_entry_tuple = (revision_number, description)
        return_list.append(list_entry_tuple)
    return return_list


parser = argparse.ArgumentParser(
    description='Create a patch file or a numbered webrev; optionally upload it to a remote location (e.g. cr.ojdk.j.n)',
    formatter_class=argparse.RawTextHelpFormatter,
    epilog=
    'This tool knows three modes:\n'
    '- Webrev Mode (default): a numbered webrev is created in the export dir.\n'
    '  Tool expects exactly one outgoing change. applied in the mercurial patch queue,\n'
    '  whose patch name will be used as name for the webrev.\n'
    '- Delta Webrev Mode (-d): like normal Webrev Mode, save that we create\n'
    '  a delta webrev in addition to the full webrev. The tool expects two\n'
    '  patches applied in the patch queue: the lower one being the patch base,\n'
    '  whose name defines the patch name; the upper (tip) one being the delta\n'
    '  (which one would later qfold into the lower full one).\n'
    '- Patch Mode: Tool creates an (unnumbered) patch in the export dir.\n'
)

# Optional args
# (Note: variable name seems to be the first encountered long (--) option name)
parser.add_argument("-v", "--verbose", dest="is_verbose",
                    help="Debug output", action="store_true")
parser.add_argument("-p", "--patch-mode", dest="patch_mode",
                    help="Patch Mode (default is Webrev Mode). In Patch Mode, creates a simple patch (diff) using hg "
                         "export.",
                    action="store_true")
parser.add_argument("-o", "--overwrite-last-webrev", dest="overwrite_last_webrev",
                    help="[Webrev mode only]: Overwrite the last webrev (\"webrev_<n>\"). If not specified, "
                         "a new webrev (\"webrev_<n+1>\") is created.",
                    action="store_true")
parser.add_argument("-d", "--delta", dest="delta_mode",
                    help="[Webrev mode only]: Produce a delta webrev in addition to the full webrev.",
                    action="store_true")
parser.add_argument("-y", dest="yesyes", help="Automatically confirm all answers (use with care).")
parser.add_argument("-u", "--upload", dest="upload", help="Upload to remote location", action="store_true")

args = parser.parse_args()
if args.is_verbose:
    trc(str(args))

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
patch_name = None
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

# name of patch is the description of the only outgoing change (not delta) resp. the
# description of the oldest outgoing change (delta mode) - in all cases, this is
# the first list item
patch_name = outgoing_changes[0][1]
trc("Patch name is " + patch_name)

patch_export_directory = export_root_dir + '/' + patch_name

if args.patch_mode:

    # patch mode:
    # Produce new patch with hg export. Delete any pre-existing patches but ask
    # user first.
    patch_file_path = patch_export_directory + '/' + patch_name + '.patch'
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
    while pathlib.Path(build_webrev_path(patch_export_directory, webrev_number_first_invalid)).exists():
        webrev_number_last_valid = webrev_number_first_invalid
        webrev_number_first_invalid += 1

    webrev_number = -1
    if args.overwrite_last_webrev and webrev_number_last_valid >= 0:
        webrev_number = webrev_number_last_valid
    else:
        webrev_number = webrev_number_first_invalid

    webrev_dir_path = build_webrev_path(patch_export_directory, webrev_number)
    delta_webrev_dir_path = build_delta_webrev_path(patch_export_directory, webrev_number)

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
        run_command_and_return_stdout(["ksh", webrev_location, "-o", webrev_dir_path])
        trc("Created new webrev at " + webrev_dir_path + " - OK.")
    else:
        # In delta mode, we create two webrevs, one for the delta part, one for the full part.

        # Delta part: use -r <rev> where revision is the parent, which in this case is the base part.
        run_command_and_return_stdout(["ksh", webrev_location, "-o", delta_webrev_dir_path, "-r",
                                      str(outgoing_changes[0][0])])
        trc("Created new delta webrev at " + delta_webrev_dir_path + " - OK.")

        # Full part: just run webrev normally without specifying a revision. It will pick up all outgoing changes,
        # which are two (base + delta)
        run_command_and_return_stdout(["ksh", webrev_location, "-o", webrev_dir_path])
        trc("Created full webrev (base + delta) at " + webrev_dir_path + " - OK.")

# upload to remote: For simplicity, I just transfer the whole patch dir, regardless if that transfers
# older webrevs too. rsync will only transfer stuff not remote already.
if args.upload:
    trc("Uploading patch...")
    destination = export_remote_user + '@' + export_remote_url + ':' + export_remote_path
    source = patch_export_directory
    result = run_command_and_return_stdout(["rsync", "-avz", "-e", "ssh", source, destination])
    trc("Did upload " + patch_export_directory + " to " + destination + " - OK.")
