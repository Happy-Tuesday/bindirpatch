# bindirpatch
This Python script creates or applies a binary diff between two directories. This is useful for creating application update patches. Internally, it uses bsdiff/bspatch on each file that was modified. It uses an index file to keep track of which files were added / modified / deleted. The result is compressed with 7zip.

## Usage
### Create Patch
`bindirpatch.py diff <oldDir> <newDir> <outDir> [options]`

This will create a patch that updates `<oldDir>` to the state in `<newDir>` and stores the resulting patch file in `<outDir>`. Note that this may take several minutes depending on the size of the content. Check out the `-j` option.

### Apply Patch
`bindirpatch.py patch <patchFile> <targetDir> [options]`

Applies the `<patchFile>` to `<targetDir>`.

### Options
|         |                                                                                             |
| ------- | ------------------------------------------------------------------------------------------- |
| `-v`    | verbose - Print more status messages                                                        |
| `-vv`   | very verbose - Print a lot of status messages (only for debugging)                          |
| `-j#`   | jobs - Run multiple jobs in parallel. Replace `#` with number of desired worker processes.  |


## Known Issues
 * There is no log output when running with multiprocessing (-j2 or above)
 * Multiprocessing is not supported for the the `patch` command, only for `diff`.
 * Only works on Windows for now


## Dependencies
### bsdiff / bspatch
You need the [Windows version of bsdiff and bspatch](http://sites.inka.de/tesla/download/bsdiff4.3-win32.zip). You also need the [command-line version of 7zip](http://www.7-zip.org/a/7z1507-extra.7z). You may need to adjust the paths to the executables in the script.
