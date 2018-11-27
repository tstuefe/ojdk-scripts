# Easy webrev generation/upload with upload-patch.py


```
usage: upload-patch.py [-h] [-v] [-p] [-d] [-y] [-n PATCH_NAME]
                       [--overwrite-last] [-u] [--openjdk-root OJDK_ROOT]
                       [--export-dir EXPORT_DIR]
                       [--webrev-script-location WEBREV_SCRIPT_LOCATION]
                       [--upload-url UPLOAD_URL]

Create a numbered webrev or a patch and optionally uploads it to a remote server using ssh.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Debug output
  -p, --patch-mode      Patch mode (default: webrev mode). In patch mode a single unnumbered patch is generated
  -d, --delta           [Webrev mode only]: Delta mode: Produce a delta webrev in addition to the full webrev. Script expects two outgoing changes, not one (base change + delta).
  -y                    Autoconfirm (use with care).
  -n PATCH_NAME, --name PATCH_NAME
                        Name of patch directory (when omitted, name is generated from the mercurial change description).
  --overwrite-last      [Webrev mode only]: Overwrite the last webrev ("webrev_<n>"). By default, a new webrev with is generated each time the script is run ("webrev_<n+1>").
  -u, --upload          Upload to remote location (see --upload-url)
  --openjdk-root OJDK_ROOT
                        Openjdk base directory - base for export directory and webrev script location. Default is /shared/projects/openjdk
  --export-dir EXPORT_DIR
                        Patch export base directory. Default: <openjdk-root-dir>/export.
  --webrev-script-location WEBREV_SCRIPT_LOCATION
                        Location of webrev script. Default: <openjdk-root-dir>/codetools/webrev/webrev.ksh.
  --upload-url UPLOAD_URL
                        Remote upload url in the form <username>@<host>:<path>. Example: john_smith@cr.openjdk.java.net:my_webrevs
```

## Basics

This tool knows two modes:
- Webrev Mode (the default): a webrev is generated into the export directory.
    - Webrevs are numbered (webrev_<n>, webrev_<n+1>). Each time the script is run a new webrev is created.
        - Exception: in "overwrite mode" `-o` or `--overwrite-last`, the highest-numbered webrev is overwritten instead 
    - Script expects exactly one outgoing change in the mercurial repository
- Patch Mode (`-p` resp. `--patch-mode`): Tool creates a simple patch in the export directory. Unlike webrevs, the patch is not numbered. This is usually faster than generating webrevs.

A special variant of webrev mode is "delta mode" (`-d` or `--delta`). Two outgoing changes are expected, the first being
 the base change, the top one the delta change. Two webrevs are created, a delta webrev for the delta change, a complete
webrev for both changes.

### Notes:

- *patch name* (name of patch directory) is automatically generated from the mercurial change description, but can be overridden with `-n` or `--name`.

## How to use it


Cd into the jdk repository. Commit or `hg qrefresh` all outstanding changes.


```
python3 upload-patch.py
```

  generates a numbered webrev from the outgoing change.

```
python3 upload-patch.py -vp
```

  generates a patch file from the outgoing change, verbose mode.

```
python3 upload-patch.py -u --upload-url thomas@cr.openjdk.java.net:my-webrevs
```

  generates a numbered webrev from the outgoing change and uploads it to cr.openjdk.java.net

```
python3 upload-patch.py -u --upload-url thomas@cr.openjdk.java.net:my-webrevs
```

  generates a numbered webrev from the outgoing change and uploads it to cr.openjdk.java.net

```
python3 upload-patch.py -d -u --overwrite-last --upload-url thomas@cr.openjdk.java.net:my-webrevs
```

  generates a numbered delta webrev (base webrev and delta) from two outgoing changes - overwriting the last one
  in the export directory - and uploads them both to cr.openjdk.java.net


