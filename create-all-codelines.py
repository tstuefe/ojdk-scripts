# !/usr/bin/env python3

# (Note: hotspot files modified in a patch:
# ack '\+\+\+ b/src/hotspot' jep387-all.patch | sed 's/+++ b\///g'
# ack '\+\+\+ b/test/hotspot/gtest' jep387-all.patch | sed 's/+++ b\///g'


import pathlib
import sys
import argparse
import os
import shutil
import subprocess

def trc(text):
    print("--- " + text)

# initialise a directory stack
pushstack = list()

def pushdir(dirname):
    global pushstack
    pushstack.append(os.getcwd())
    verbose("-> " + dirname)
    os.chdir(dirname)


def popdir():
    global pushstack
    last_dir = pushstack.pop()
    verbose("<- " + last_dir)
    os.chdir(last_dir)


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


def error_exit(text):
    print('*** ERROR: ' + text)
    sys.exit(':-(')


def verbose(text):
    if args.is_verbose:
        print("--- " + text)


def delete_directory_safe(dir):
    fulldir = str(pathlib.Path(dir).resolve())
    if fulldir.startswith(openjdk_root) and openjdk_root is not None and len(openjdk_root) > 0 and len(fulldir) > len(openjdk_root):
        verbose("Deleting " + fulldir)
        shutil.rmtree(fulldir)


openjdk_root = os.getcwd()
gtest_dir = openjdk_root + "/gtest"
bootjdk = "sapmachine15"


def write_lines_to_file(lines, filename):
    # append newline to all lines
    lines = [e + "\n" for e in lines]
    f = open(filename, "w")
    f.writelines(lines)
    f.close()


# call from within codeline dir
def create_output_directory(output_configuration, configure_args):
    output_dir_name = "output-" + output_configuration
    pathlib.Path("output-" + output_configuration).mkdir(parents=False, exist_ok=True)


# call from within codeline dir
def create_output_directories():
    option_bootjdk = "--with-boot-jdk=" + openjdk_root + "/jdks/" + bootjdk + " "
    option_fastdebug = "--with-debug-level=fastdebug "
    option_slowdebug = "--with-debug-level=slowdebug "
    option_release = "--with-debug-level=release "
    option_nopch = "--disable-precompiled-headers "
    option_gtest = "--with-gtest=" + gtest_dir + "/googletest "
    option_bit32 = "--with-target-bits=32 "
    option_zero = "--with-jvm-variants=zero "
    option_minimal = "--with-jvm-variants=minimal "

    standard_options = option_bootjdk + option_gtest

    names_and_configure_lines = [
        ["fastdebug",           standard_options + option_fastdebug + option_nopch],
        ["slowdebug",           standard_options + option_slowdebug],
        ["release",             standard_options + option_release + option_nopch],
        ["fastdebug-32",        standard_options + option_fastdebug + option_bit32 + option_nopch],
        ["fastdebug-zero",      standard_options + option_fastdebug + option_zero],
        ["minimal",             standard_options + option_fastdebug + option_nopch + option_minimal],
    ]

    for x in names_and_configure_lines:
        pathlib.Path("output-" + x[0]).mkdir(parents=False, exist_ok=True)

    # create a single bash to init all configure lines. Just runs configure in all output dirs.
    lines = [
        "#!/bin/bash",
        "set -e"
    ]

    for x in names_and_configure_lines:
        lines.append("pushd output-" + x[0])
        lines.append("bash ../source/configure " + x[1])
        lines.append("popd")

    write_lines_to_file(lines, "run-all-configure.sh")

# Initialize a codeline directory (before getting the sources)
def init_codeline_directory_1(codeline_name):

    if args.clean and pathlib.Path(codeline_name).exists():
        pushdir(codeline_name)
        trc("Cleaning codeline dir...")
        # delete all but the existing source folder from the codeline dir:
        to_delete = [f for f in os.listdir('.') if f != "source"]
        for f in to_delete:
            trc("f" + f)
            if pathlib.Path(f).is_dir():
                delete_directory_safe(f)
            else:
                os.remove(f)
        popdir()

    # Create directory and output directories
    pathlib.Path(codeline_name).mkdir(parents=False, exist_ok=True)

    pushdir(codeline_name)

    create_output_directories()

    # put down a script to prepare the intellij workspace (see
    # https://github.com/tstuefe/docs/blob/master/intellij-ojdk-setup.md)
    write_lines_to_file([
        "#!/bin/bash",
        "mkdir source/build",
        "pushd source/build",
        "ln -s ../../output-fastdebug linux-x86_64-normal-server-fastdebug",
        "popd",
        ". /shared/projects/ant/setenv.sh"
        "bash ./bin/idea.sh"
    ], "intellij_init.sh")

    # Also create the CDT workspace. We give it a good name since the name shows up in
    #  Eclipse and helps telling apart running cdt instances
    cdt_workspace_dir = "cdt-ws-" + codeline_name
    if pathlib.Path(cdt_workspace_dir).exists():
        trc(cdt_workspace_dir + " found, skipping.")
    else:
        run_command_and_return_stdout(["git", "clone", "git@github.com:tstuefe/ojdk-cdt.git", cdt_workspace_dir])

    popdir()


# call from within opendjk root dir
def create_codeline_directory_from_git(codeline_name, git_url, git_branch):
    init_codeline_directory_1(codeline_name)
    pushdir(codeline_name)
    if not pathlib.Path("source").exists():
        run_command_and_return_stdout(["git", "clone", git_url, "source"])
        pushdir("source")
        run_command_and_return_stdout(["git", "checkout", git_branch])
        popdir()
    popdir()


# JDKs in a unified mercurial repo
def create_codeline_directory_from_mercurial_unified(codeline_name, hg_url):
    init_codeline_directory_1(codeline_name)
    pushdir(codeline_name)
    if not pathlib.Path("source").exists():
        run_command_and_return_stdout(["hg", "clone", hg_url, "source"])
    popdir()

# JDKs in a forest repo
def create_codeline_directory_from_mercurial_forest(codeline_name, hg_url):
    init_codeline_directory_1(codeline_name)
    pushdir(codeline_name)
    if not pathlib.Path("source").exists():
        run_command_and_return_stdout(["hg", "clone", hg_url, "source"])
        pushdir("source")
        run_command_and_return_stdout(["bash", "get_source.sh"])
        popdir()
    popdir()


def create_jdks_directory_if_needed():
    pathlib.Path("jdks").mkdir(parents=False, exist_ok=True)
    pushdir("jdks")
    if pathlib.Path("sapmachine11").exists():
        trc("jdks/sapmachine11 found, skipping.")
    else:
        run_command_and_return_stdout(["wget", "https://github.com/SAP/SapMachine/releases/download/sapmachine-11.0.8/sapmachine-jdk-11.0.8_linux-x64_bin.tar.gz"])
        run_command_and_return_stdout(["tar", "--one-top-level=sapmachine11", "--strip-components=1", "-xf", "sapmachine-jdk-11.0.8_linux-x64_bin.tar.gz"])
    if pathlib.Path("sapmachine15").exists():
        trc("jdks/sapmachine15 found, skipping.")
    else:
        run_command_and_return_stdout(["wget", "https://github.com/SAP/SapMachine/releases/download/sapmachine-15/sapmachine-jdk-15_linux-x64_bin.tar.gz"])
        run_command_and_return_stdout(["tar", "--one-top-level=sapmachine15", "--strip-components=1", "-xf", "sapmachine-jdk-15_linux-x64_bin.tar.gz"])
    popdir()


########################################

parser = argparse.ArgumentParser(description='Create openjdk codeline dirs')

parser.add_argument("-v", "--verbose", dest="is_verbose", default=False,
                    help="Debug output", action="store_true")

parser.add_argument("-c", "--clean", dest="clean", default=False,
                    help="Clear old codeline dirs from all but the sources themselves", action="store_true")

args = parser.parse_args()
if args.is_verbose:
    trc(str(args))

#####################################

# Download boot jdk if necessary
create_jdks_directory_if_needed()

# if gtest suite is missing, get it
if not pathlib.Path(gtest_dir).exists():
    run_command_and_return_stdout(["git", "clone", "git@github.com:tstuefe/ojdk-gtest.git", "gtest"])

create_codeline_directory_from_git("jdk-jdk",           "git@github.com:tstuefe/jdk.git", "master")

create_codeline_directory_from_git("jdk-jdk-orig",       "https://github.com/openjdk/jdk.git", "master")

create_codeline_directory_from_git("sapmachine-head",   "git@github.com:tstuefe/SapMachine.git", "sapmachine")

create_codeline_directory_from_git("sapmachine-11",     "git@github.com:tstuefe/SapMachine.git", "sapmachine11")

create_codeline_directory_from_mercurial_unified("jdk-jdk11u-dev", "http://hg.openjdk.java.net/jdk-updates/jdk11u-dev/")

create_codeline_directory_from_mercurial_forest("jdk-jdk8u-dev", "http://hg.openjdk.java.net/jdk8u/jdk8u-dev/")

