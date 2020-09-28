# !/usr/bin/env python3

# (Note: hotspot files modified in a patch:
# ack '\+\+\+ b/src/hotspot' jep387-all.patch | sed 's/+++ b\///g'
# ack '\+\+\+ b/test/hotspot/gtest' jep387-all.patch | sed 's/+++ b\///g'


import pathlib
import sys
import os
import argparse


def trc(text):
    print("--- " + text)


def error_exit(text):
    print('*** ERROR: ' + text)
    sys.exit(':-(')


def verbose(text):
    if args.is_verbose:
        print("--- " + text)


def has_extension(filename, extensions):
    extension = pathlib.Path(filename).suffix
    if extension in extensions:
        return True
    else:
        return False


def is_source_file(filename):
    return has_extension(filename, {".cpp", ".c"})


def is_header_file(filename):
    return has_extension(filename, {".hpp", ".h"})


def should_process_this_file(filename):
    return is_source_file(filename) or is_header_file(filename)


# given a directory, find files in it to process and add to output list
def find_files_to_process(directory):
    return_list = []
    files_in_dir = os.listdir(directory)
    for f in files_in_dir:
        f_full = directory + "/" + f
        if os.path.isdir(f_full):
            return_list = return_list + find_files_to_process(f_full)
        else:
            if should_process_this_file(f_full):
                return_list.append(f_full)
    return return_list


def is_nonempty_line(line):
    if line.strip() != "":
        return True
    else:
        return False

# Given a number of lines, fix an include block according to hotspot rules
#   - sort all includes alphabetically
#   - remove empty lines in include block
#   - for source files, prepend precompiled header
# It modifies the input list.
# Returns True if successful, False if not
def fix_include_block(lines, is_source_file):

    line_no = 0
    first_include_line_no = -1
    last_include_line_no = -1

    # Extract include section.
    for line in lines:
        line_stripped = line.strip()
        if first_include_line_no == -1:
            if line_stripped.startswith('#include'):
                first_include_line_no = line_no
                last_include_line_no = line_no
        else:
            if line_stripped.startswith('#include'):
                last_include_line_no = line_no
            else:
                if line_stripped != "":
                    # found first non-include line. We are done.
                    break
        line_no += 1

    if first_include_line_no == -1:
        trc("Did not find include section.")
        if is_source_file:
            return False
        else:
            return True  # accept this for headers.

    include_lines = lines[first_include_line_no: last_include_line_no + 1]

    # Special rule applies for cpp files: whatever we sort, precompiled.cpp
    # shall be the first include. We remove the include before sorting and re-insert
    # it afterwards.
    include_precompiled = None
    if is_source_file:
        if include_lines[0].strip() != '#include \"precompiled.hpp\"':
            trc("Weird: did not find precompiled.hpp at first position. Found: " + include_lines[0])
            return False
        include_precompiled = include_lines[0]
        del include_lines[0]

    # remove empty lines from includes
    include_lines = list(filter(is_nonempty_line, include_lines))

    # Sort the includes.
    include_lines.sort()

    # re-add precompiled.hpp at pos 0
    if include_precompiled is not None:
        include_lines.insert(0, include_precompiled)

    # Now exchange the includes in the original lines
    lines[first_include_line_no: last_include_line_no + 1] = include_lines

    return True


# Given a number of lines, squash all multiple empty lines into one
# It modifies the input list.
# Returns True if successful, False if not
def squash_multiple_empty_lines(lines):
    had_empty_line = False
    lines2 = []
    for line in lines:
        if line.strip() == "":
            if had_empty_line:
                pass
            else:
                lines2.append(line)
                had_empty_line = True
        else:
            lines2.append(line)
            had_empty_line = False
    lines[:] = lines2
    return True


# Given a number of lines, fix my common whitespace issues:
#  - remove trailing white spaces
#  - exchange tab to two spaces
#  - add a space after loop keywords (for, while)
# Returns True if successful, False if not
def fix_whitespaces(lines):
    lines2 = []
    for line in lines:
        line_stripped = line.rstrip()
        line_stripped = line_stripped.replace('\t', '  ')
        line_stripped = line_stripped.replace(' for(', ' for (')
        line_stripped = line_stripped.replace(' while(', ' while (')
        lines2.append(line_stripped + "\n")
    lines[:] = lines2
    return True


def form_include_guard_name(full_path_of_header):
    index = full_path_of_header.find('/src/hotspot/')
    if index == -1:
        return ""
    f = full_path_of_header[index + 13:]
    f = f.upper()
    f = f.replace('.', '_')
    f = f.replace('/', '_')
    return f


# fix include guards.
def fix_include_guards(lines, full_path_of_header):

    line_no = 0
    lineno_ifdef = -1
    lineno_def = -1
    lineno_endif = -1

    include_guard_name = form_include_guard_name(full_path_of_header)
    if include_guard_name == "":
        return False

    # search include guard definition (just the first ifdef define pair)
    for line in lines:
        if lineno_ifdef == -1 and line.startswith('#ifndef '):
            lineno_ifdef = line_no
        elif lineno_ifdef != -1 and lineno_def == -1:
            if not line.strip().startswith('#define'):
                trc("malformed include guard?")
                return False
            lineno_def = line_no
        elif lineno_ifdef != -1 and lineno_def != -1:
            if line.startswith('#endif'):
                lineno_endif = line_no
            elif line.strip() != "":
                lineno_endif = -1
        line_no += 1

    lines[lineno_ifdef] = "#ifndef " + include_guard_name + "\n"
    lines[lineno_def] = "#define " + include_guard_name + "\n"
    lines[lineno_endif] = "#endif // " + include_guard_name + "\n"

    return True

#####################

parser = argparse.ArgumentParser(description='Fix include order in hotspot files.')

parser.add_argument("-v", "--verbose", dest="is_verbose", default=False,
                    help="Debug output", action="store_true")

parser.add_argument("-R", "--recursive", dest="recursive", default=False,
                    help="Fix files recursively", action="store_true")

parser.add_argument("--dry-run", dest="dry_run", default=False, action="store_true",
                    help="Squawk but don't leap.")

parser.add_argument("-i", "--fix-include-blocks", dest="fix_include_blocks", default=False,
                    help="Fix order of includes in include blocks and remove newlines.", action="store_true")

parser.add_argument("-g", "--fix-include-guards", dest="fix_include_guards", default=False,
                    help="Fix names of include guards.", action="store_true")

parser.add_argument("-w", "--fix-whitespaces", dest="fix_whitespaces", default=False,
                    help="Fix whitespace issues.", action="store_true")

parser.add_argument("-n", "--squash-empty-lines", dest="squash_empty_lines", default=False,
                    help="Squash multiple empty lines into one.", action="store_true")

parser.add_argument("-a", "--all", dest="allall", default=False,
                    help="Run all fixes.", action="store_true")

parser.add_argument("--from-patch-file", dest="from_patch_file", default=False,
                    help="use a patch file to find out which files to test.", action="store_true")

# parser.add_argument("-c", "--codeline", default=default_codeline, metavar="CODELINE",
#                    help="Codeline (repository) to build. Default: %(default)s. Valid values: %(choices)s.",
#                    choices=valid_codelines)

# positional args
parser.add_argument("files", default=[], nargs='+', metavar="FILES",
                    help="Files to scanVariant(s) to build. Default: %(default)s. "
                         "Valid values: %(choices)s.")

args = parser.parse_args()
if args.is_verbose:
    trc(str(args))

################################################
# first build up a list of files by resolving directories recursively.
# Also, we only deal with c/c++ files

VALID_EXTENSIONS = ["cpp", "c", "hpp", "h"]

files_to_process = []

# First off, find out which files to process. All files are given on the command line,
# unless --from-patch-file is given, in which case we expect the patch file to contain all
# the files to modify (todo)

for f in args.files:
    if not os.path.exists(f):
        error_exit("File not found: " + f)

    if os.path.isdir(f) and args.recursive:
        files_to_process = files_to_process + find_files_to_process(f)
    else:
        if should_process_this_file(f):
            files_to_process.append(f)

for f in files_to_process:

    verbose("Processing " + f + "...")

    input_lines = []
    success = True

    # Read in file
    with open(f) as file_in:
        input_lines = file_in.readlines()
        file_in.close()

    verbose(str(len(input_lines)) + " lines read...")

    output_lines = input_lines.copy()

    # Mofidy ....
    if args.fix_include_blocks or args.allall:
        success &= fix_include_block(output_lines, is_source_file(f))

    if args.squash_empty_lines or args.allall:
        success &= squash_multiple_empty_lines(output_lines)

    if args.fix_whitespaces or args.allall:
        success &= fix_whitespaces(output_lines)

    if args.fix_include_guards  or args.allall:
        if is_header_file(f):
            success &= fix_include_guards(output_lines, str(pathlib.Path(f).absolute()))

    # do other stuff....

    # ignore files which feel iffy
    if not success:
        trc(f + ": unclear. Please fix manually.")
        continue

    # output: if any of the previous steps changed the file, and dry-run is not active,
    # write out the changed file.
    if input_lines != output_lines:
        trc("Fixing " + f)
        if args.dry_run:
            trc(" (dry run. Nothing changed.)")
        else:
            with open(f, mode='w') as file_out:
                file_out.writelines(output_lines)
