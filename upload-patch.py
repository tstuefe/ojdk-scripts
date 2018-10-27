
#!/usr/bin/env python3

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
    if args.is_verbose:
        print(text)

def run_command_and_return_stdout (command):
    trc('----')
    trc('calling: ' + ' '.join(command))
    try:
        stdout = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        print('Command failed ' + ' '.join(command))
        print(e)
        sys.exit('Sorry :-(')
    stdout = stdout.decode("utf-8")
    trc('out: ' + stdout)
    trc('----')
    return stdout

def build_patch_directory_path(patch_name):
    return export_root_dir + '/' + patch_name

def build_webrev_path(patch_name, webrev_number):
    return build_patch_directory_path(patch_name) + '/webrev_' + str(webrev_number)

def build_patch_path(patch_name):
    return build_patch_directory_path(patch_name) + '/' + patch_name + '.patch'

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

parser = argparse.ArgumentParser(description='Upload a patch to cr.ojdk.j.n')

# Optional args
# (Note: variable name seems to be the first encountered long (--) option name)
parser.add_argument("-v", "--verbose", dest="is_verbose",
                    help="Debug output", action="store_true")
parser.add_argument("-p", "--patch-mode", dest="patch_mode", help="Patch mode (creates a patch file using hg export)", action="store_true")
parser.add_argument("-w", "--webrev-mode", dest="webrev_mode", help="Webrev mode (creates a webrev using webrev.ksh. This is the default.", action="store_true")
parser.add_argument("-i", "--increase-webrev-number", dest="inc_webrev_number",
                    help="Webrev mode only: When writing the webrev, increase the webrev number. By default, we overwrite the highest webrev.", action="store_true")
parser.add_argument("-y", dest="yesyes", help="Anser YES automatically to all questions")
parser.add_argument("-n", "--no-upload", dest="no_upload", help="Omit upload - just export the patch or webrev to the export directory", action="store_true")

args = parser.parse_args()

#---

# sanity: -p and -w are mutually exclusive
if args.patch_mode and args.webrev_mode:
    sys.exit("Specify either -p or -w, but not both.")
elif args.patch_mode:
    is_patch_mode = True
    is_webrev_mode = False
else:
    is_webrev_mode = True
    is_patch_mode = False


# sanity: -n makes only sense in webrev mode
if args.inc_webrev_number == True and is_patch_mode:
    sys.exit("Option -i only supported in webrev mode.")

# run hg qapplied. That should give us exaclty one line, since we expect only one patch applied.
qapplied_result = run_command_and_return_stdout(['hg', 'qapplied']).splitlines()
if len(qapplied_result) == 0:
    sys.exit('Mercurial queue is empty')
elif len(qapplied_result) > 1:
    sys.exit('Multiple patches applied. This script only works with exaclty one patch.')

patch_name = qapplied_result[0]
trc('Exactly one patch applied (' + patch_name + ') - OK.')

# check that all changes are qrefresh'ed
open_changes = run_command_and_return_stdout(['hg', 'diff'])
if open_changes != '':
    sys.exit('There are open changes in the workspace. Please qrefresh first.')
else:
    trc('No outstanding changes in workspace - OK.')

# export directory must exist
if not pathlib.Path('../../export').exists():
    sys.exit('export directory not found (../../export)')

# create export directory
patch_directory = build_patch_directory_path(patch_name)
pathlib.Path(patch_directory).mkdir(parents=True, exist_ok=True) 

# Calculate the full export path. For a patch, this is the patch to the (unnumbered) patch file. For webrevs,
# the patch to the numbered webrev directory.

if is_patch_mode:
    full_export_path = build_patch_path(patch_name)
else:
    # webrev mode:
    # First, find existing highest webrev in export dir
    webrev_number = 0
    while pathlib.Path(build_webrev_path(patch_name, webrev_number)).exists():
        trc("Found pre-existing: " + build_webrev_path(patch_name, webrev_number))
        webrev_number += 1
    # by default, we overwrite the highest one. Unless -i is specified, then we increase.
    if not args.inc_webrev_number == True:
        if webrev_number > 0:
            webrev_number -= 1
    full_export_path = build_webrev_path(patch_name, webrev_number)

trc("Export path is: " + full_export_path)

# Delete pre-existing. But ask beforehand.
if pathlib.Path(full_export_path).exists():
    if is_patch_mode:
        user_confirm('Remove pre-existing patch: ' + full_export_path)
        trc("Removing pre-existing patch at " + full_export_path + "...")
        pathlib.Path(full_export_path).unlink()
        trc("OK.")
    else:
        # webrev mode
        user_confirm('Remove pre-existing webrev: ' + full_export_path)
        trc("Removing pre-existing directory at " + full_export_path + "...")
        shutil.rmtree(full_export_path)
        trc("OK.")
else:
    trc("No preexisting patch/webrev found - OK.")

# Produce the webrev, patch:
if is_patch_mode:
    trc("Exporting patch...")
    result = run_command_and_return_stdout(["hg", "export", "-o", full_export_path])
    print(result)
    trc("OK.")
else:
    trc("Creating webrev...")
    result = run_command_and_return_stdout(["ksh", webrev_location, "-o", full_export_path])
    print(result)
    trc("Webrev successfully created - OK.")

# upload to remote: For simplicity, I just transfer the whole patch dir, regardless if that transfers
# older webrevs too. rsync will only transfer stuff not remote already.
if args.no_upload:
    trc("--export-only specified: omitting upload.")
else:
    trc("Uploading patch...")
    destination = export_remote_user + '@' + export_remote_url + ':' + export_remote_path
    source = export_root_dir + '/' + patch_name
    result = run_command_and_return_stdout(["rsync", "-avz", "-e", "ssh", source, destination])
    print(result)
    trc("OK.")




