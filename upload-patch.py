
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

def build_webrev_path(patch_name, webrev_number):
    return export_root_dir + '/' + patch_name + '/webrev_' + str(webrev_number)

def build_patch_path(patch_name):
    return export_root_dir + '/' + patch_name + '/' + patch_name + '.patch'

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
parser.add_argument("-p", "--patch", dest="patch_mode", help="Make a patch (default: make a webrev)", action="store_true")
parser.add_argument("-n", "--webrev-number", dest="webrevno", type=int, help="Webrev number. By default, numbers are incremented automatically in the export dir.")
parser.add_argument("-e", "--export-only", help="Omit upload - just export the patch or webrev to the export directory")
parser.add_argument("-y", dest="yesyes", help="Anser YES automatically to all questions")

args = parser.parse_args()

#---

# sanity: -n makes only sense in webrev mode
if args.webrevno is not None and args.patch_mode:
    sys.exit("Option -n|--webrev-number only supported in webrev mode.")

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
pathlib.Path('../../export/' + patch_name).mkdir(parents=True, exist_ok=True) 

# Calculate the full export path. For a patch, this is the patch to the (unnumbered) patch file. For webrevs,
# the patch to the numbered webrev directory.
full_export_path = ""
    
if args.patch_mode:
    full_export_path = build_patch_path(patch_name)
else:
    # webrev mode:
    # by default, we search in the export directory for the highest numbered webrev
    # and add one. If -n is given, we use that number.
    webrev_number = 0
    if args.webrevno is None:
        while pathlib.Path(build_webrev_path(patch_name, webrev_number)).exists():
            webrev_number += 1
    else:
        # override number
        webrev_number = args.webrevno
    full_export_path = build_webrev_path(patch_name, webrev_number)

trc("Export path is: " + full_export_path)

if not args.patch_mode:
    # Sanity checks for webrev mode:
    if args.webrevno is not None:
        # if number is forced: there must not exist a webrev with a higher number in the export dir
        # (e.g. -n 10 should not create webrev_10 if there already exist webrev_11++) since this
        # most probably is a user error
        next_theoretical_webrev = build_webrev_path(patch_name, webrev_number + 1)
        if pathlib.Path(next_theoretical_webrev).exists():
            sys.exit('webrev number forced to ' + str(args.webrevno) + " but higher numbered webrevs found - aborting.")

# if there is a preexisting export: ask before deleting
if pathlib.Path(full_export_path).exists():
    if args.patch_mode:
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
if args.patch_mode:
    trc("Exporting patch...")
    result = run_command_and_return_stdout(["hg", "export", "-o", full_export_path])
    print(result)
    trc("OK.")
else:
    trc("Creating webrev...")
    result = run_command_and_return_stdout(["ksh", webrev_location, "-o", full_export_path])
    print(result)
    trc("OK.")

