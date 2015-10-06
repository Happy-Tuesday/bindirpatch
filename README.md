# Overview
This is a collection of tools for managing application updates. It consists of the following tools:
 - **bindirpatch**: Creates and applies diffs between two directories 
 - **deploy**: Creates a patch, manages version numbers and uploads to an FTP server 
 - **autoupdate**: Checks FTP server for new version and installs updates 

The bindirpatch tool works standalone and has no dependencies to the other scripts (except for utils.py). The deploy and autoupdate scripts are meant to be used together. They require an FTP server that should have two user accounts, one with read-only access and one with write access. The server will always have the latest version of the application, along with a history of patches that can be used to update previous versions. 

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
You need the [Windows version of bsdiff and bspatch](http://sites.inka.de/tesla/download/bsdiff4.3-win32.zip). You also need the [command-line version of 7zip](http://www.7-zip.org/a/7z1507-extra.7z). You may need to adjust the paths to the executables in the script.


# deploy 
This is the script used by the developer to deploy a new update. It automatically increments the version number, creates a patch from the old to the new version, then uploads the patch and the full new version to the server.

## Usage 
`deploy.py <oldDir> <newDir> <tempDir> <outDir> <url> <user> <password> <remotePath> [options]`

### Arguments
|            |                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------- |
| oldDir     | last uploaded build (current latest build on server)                                        |
| newDir     | build to be deployed                                                                        |
| tempDir    | Where to put temp files. This directory will be deleted!                                    |
| outDir     | where to put the result files                                                               |
| url        | url of the ftp server                                                                       |
| user       | username for uploading on the server                                                        |
| password   | password for ftp user                                                                       |
| remotePath | path on the ftp server to store the files                                                   |

### Options 
|         |                                                                                             |
| ------- | ------------------------------------------------------------------------------------------- |
| `-j#`   | jobs - Run multiple jobs in parallel. Replace `#` with number of desired worker processes.  |


# autoupdate 
This is the script used on the client side to update the application to the newest version. It does this by downloading all available patches and installing them in the correct order.

If the application cannot be found at the given directory, the latest version is downloaded from the server and installed there.

Similarly, if the installed version is so far behind that downloading the patches would take more traffic than downloading the full application archive, the tool detects this and downloads the new version right away.

## Usage 
`autoupdate.py <projectDir> <tempDir> <serverUrl> [options]`

### Arguments 
|            |                                            |
| ---------- | ------------------------------------------ |
| projectDir | Path to the application directory.         |
| tempDir    | Path to a temporary working directory.     |
| serverUrl  | url of the ftp server                      |

### Options 
|         |                                                                       |
| ------- | --------------------------------------------------------------------- |
| `-aU:P` | Authentication, Username:Password, ex: -aexampleuser:examplepassword  |
| `pPath` | path on the ftp server where the files are stored                     |
