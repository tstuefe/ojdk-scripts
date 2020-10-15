# !/usr/bin/env python3

# (Note: hotspot files modified in a patch:
# ack '\+\+\+ b/src/hotspot' jep387-all.patch | sed 's/+++ b\///g'
# ack '\+\+\+ b/test/hotspot/gtest' jep387-all.patch | sed 's/+++ b\///g'


import pathlib
import sys
import argparse
import os
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


openjdk_root = os.getcwd()
gtest_dir = openjdk_root + "/gtest"
bootjdk = "sapmachine15"


def write_lines_to_file(lines, filename):
    f = open(filename, "w")
    f.writelines(lines)
    f.close()


# call from within codeline dir
def create_output_directory(output_configuration, configure_args):
    pathlib.Path("output_" + output_configuration).mkdir(parents=False, exist_ok=True)
    # Note: the configure commands cannot be put into the output folder since configure will fail
    #  for non-empty folders
    lines = ["bash ../source/configure " + configure_args + "\n"]
    write_lines_to_file(lines, "configure_" + output_configuration + ".sh")


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

    standard_options = option_bootjdk + option_gtest

    names_and_configure_lines = [
        ["fastdebug",           standard_options + option_fastdebug],
        ["fastdebug-nopch",     standard_options + option_fastdebug + option_nopch],
        ["slowdebug",           standard_options + option_slowdebug],
        ["release",             standard_options + option_release],
        ["fastdebug-32",        standard_options + option_fastdebug + option_bit32],
        ["fastdebug-zero",      standard_options + option_fastdebug + option_zero],
    ]

    for x in names_and_configure_lines:
        create_output_directory(x[0], x[1])


# call from within opendjk root dir
def init_codeline_directory_1(codeline_name):

    # Create directory and output directories
    pathlib.Path(codeline_name).mkdir(parents=False, exist_ok=True)

    pushdir(codeline_name)

    create_output_directories()

    # put down a script to prepare the intellij workspace (see
    # https://github.com/tstuefe/docs/blob/master/intellij-ojdk-setup.md)
    write_lines_to_file([
        "#!/bin/bash\n",
        "mkdir source/build\n",
        "pushd source/build\n",
        "ln -s ../../output-fastdebug linux-x86_64-normal-server-fastdebug\n",
        "popd\n",
        ". /shared/projects/ant/setenv.sh\n"
        "bash ./bin/idea.sh\n"
    ], "prepare_intellij_workspace.sh")

    # Also create the CDT workspace. We give it a good name since the name shows up in
    #  Eclipse and helps telling apart running cdt instances
    cdt_workspace_dir = "cdt_ws_" + codeline_name
    if not pathlib.Path(cdt_workspace_dir).exists():
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
    if not pathlib.Path("sapmachine15").exists():
        run_command_and_return_stdout(["wget", "https://github.com/SAP/SapMachine/releases/download/sapmachine-15/sapmachine-jdk-15_linux-x64_bin.tar.gz"])
        run_command_and_return_stdout(["tar", "-xf", "sapmachine-jdk-15_linux-x64_bin.tar.gz"])
        run_command_and_return_stdout(["mv", "sapmachine-jdk-15", "sapmachine15"])
    popdir()


########################################

parser = argparse.ArgumentParser(description='Create openjdk codeline dirs')

parser.add_argument("-v", "--verbose", dest="is_verbose", default=False,
                    help="Debug output", action="store_true")

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
create_codeline_directory_from_git("jdk-jdk-original",  "https://github.com/openjdk/jdk.git", "master")

create_codeline_directory_from_git("sapmachine-head",   "git@github.com:tstuefe/SapMachine.git", "sapmachine")
create_codeline_directory_from_git("sapmachine11",      "git@github.com:tstuefe/SapMachine.git", "sapmachine11")

#create_codeline_directory_from_mercurial_unified("jdk-jdk11u-dev", "http://hg.openjdk.java.net/jdk-updates/jdk11u-dev/")

#create_codeline_directory_from_mercurial_forest("jdk-jdk8u-dev", "http://hg.openjdk.java.net/jdk8u/jdk8u-dev/")

