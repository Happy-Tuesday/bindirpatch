import bindirpatch
import shutil
import sys
import os
from ftplib import FTP
from utils import unzip_directory, find_application_version, Progress

"""
    Ensures that the latest version of an application is installed.

    Application must have a VERSION file in its root directory that contains the version number.
    Version number must be continuously numbered. You can't skip a number (e.g. go from v57 to v60),
    because then the updater would think that v57 is the latest version.
    
    Update Server must have following directory structure:
    www.example.com/some/path/latest        -> latest version of the application as 7z archive
    www.example.com/some/path/patches/v2    -> patch from v1 to v2
    www.example.com/some/path/patches/v3    -> patch from v2 to v3
    ...                                     -> there must be a patch for every version
"""

PROJECT_DIR = ''
TEMP_DIR = ''
UPDATE_SERVER_URL = ''
UPDATE_SERVER_USER = 'anonymous'
UPDATE_SERVER_PWD = 'anonymous'
UPDATE_SERVER_PATH = '/'

class AutoUpdateException(Exception):
    def __init__(self, arg):
        self.args = arg

class ConnectionError(AutoUpdateException):
    def __init__(self, arg):
        self.args = arg


def update_application():
    ftp = ftp_connect()
    
    currentVersion = find_current_version()
    if currentVersion == None:
        print 'Could not find current version'
        download_full_game(ftp)
        return
    
    (patches, numPatchBytes) = find_available_patches(ftp)
    if len(patches) == 0:
        print 'Already up to date.'
        return

    fullGameBytes = find_full_game_size(ftp)
    if numPatchBytes > fullGameBytes:
        print 'Too far behind'
        download_full_game(ftp)
        return

    download_patches(ftp, patches, numPatchBytes)
    ftp.quit()

    install_patches(patches)
        

def ftp_connect():
    print 'Connecting to Server'
    ftp = FTP(UPDATE_SERVER_URL)
    ftp.login(UPDATE_SERVER_USER, UPDATE_SERVER_PWD)
    ftp.cwd(UPDATE_SERVER_PATH)
    return ftp
    
    
def find_current_version():
    return find_application_version(PROJECT_DIR)


def clear_temp_dir():
    if os.path.exists(TEMP_DIR):
        os.rename(TEMP_DIR, TEMP_DIR + '_deleteme')
        shutil.rmtree(TEMP_DIR + '_deleteme')
    os.makedirs(TEMP_DIR)


def find_available_patches(ftp):
    print 'Checking for Updates...'
    currentVersion = find_current_version()
    remoteBaseDir = ftp.pwd()
    ftp.cwd('patches')

    patches = ftp.nlst()
    patches = sorted(patches)
    patches = [x for x in patches if x[1:].isdigit() and int(x[1:]) > currentVersion]
    
    totalBytes = 0
    for patch in patches:
        ftp.voidcmd('TYPE I')
        totalBytes += ftp.size(patch)

    ftp.cwd(remoteBaseDir)
    return (patches, totalBytes)


def download_patches(ftp, patches, numPatchBytes):
    print 'Downloading ' + str(len(patches)) + ' Patches (' + str(numPatchBytes / 1000000) + ' MB)'
    clear_temp_dir()
    progress = Progress(numPatchBytes, 50)
    progress.print_header(10)

    remoteBaseDir = ftp.pwd()
    ftp.cwd('patches')
    
    for patch in patches:
        download_file(ftp, patch, os.path.join(TEMP_DIR, patch), progress)

    ftp.cwd(remoteBaseDir)


def install_patches(patches):
    for patch in patches:
        print 'Installing patch ' + patch
        patchFilePath = os.path.join(TEMP_DIR, patch)
        bindirpatch.apply_patch(patchFilePath, PROJECT_DIR)
    shutil.rmtree(TEMP_DIR)
    

def find_full_game_size(ftp):
    ftp.voidcmd('TYPE I')
    return ftp.size('latest')

def download_full_game(ftp):
    fileSize = find_full_game_size(ftp)
    print 'Downloading full application (' + str(fileSize / 1000000) + ' MB)...'
    clear_temp_dir()
    progress = Progress(fileSize, 50)
    progress.print_header(10)
    filename = os.path.join(TEMP_DIR, 'latest')
    download_file(ftp, 'latest', filename, progress)
    print 'Extracting files...'
    unzip_directory(filename, TEMP_DIR)
    if os.path.exists(PROJECT_DIR):
        print 'Deleting old files...'
        shutil.rmtree(PROJECT_DIR)
    print 'Copying new files...'
    os.rename(os.path.join(TEMP_DIR, 'bin'), PROJECT_DIR)
    shutil.rmtree(TEMP_DIR)
    print 'Done.'


def download_file(ftp, remoteFileName, outFileName, progress):
    with open(outFileName, 'wb') as outFile:
        def write_downloaded_block(block):
            outFile.write(block)
            progress.add_progress(len(block))
        ftp.retrbinary('RETR ' + remoteFileName, write_downloaded_block, 102400)


def parseExtraArgs(i):
    global UPDATE_SERVER_USER, UPDATE_SERVER_PWD, UPDATE_SERVER_PATH
    if len(sys.argv) <= i:
        return
    arg = sys.argv[i]
    if arg.startswith('-a'):
        (user, pw) = arg[2:].split(':', 1)
        UPDATE_SERVER_USER = user
        UPDATE_SERVER_PWD = pw
    elif arg.startswith('-p'):
        UPDATE_SERVER_PATH = arg[2:]
        if not UPDATE_SERVER_PATH.startswith('/'):
            UPDATE_SERVER_PATH = '/' + UPDATE_SERVER_PATH
    else:
        print 'Invalid argument: ' + sys.argv[i]
        usage()
    parseExtraArgs(i+1)
    

def usage():
    print 'Usage: python autoupdate.py <projectDir> <tempDir> <serverUrl> [options]'
    print ''
    print 'Options:'
    print ' -aU:P   Authentication, (Username:Password), ex: -auser101:abc123'
    print ' -pPath  Set base path on the remove server.'
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        usage()
        
    PROJECT_DIR = sys.argv[1]
    TEMP_DIR = sys.argv[2]
    UPDATE_SERVER_URL = sys.argv[3]
    parseExtraArgs(4)

    #print 'Project Dir: ', PROJECT_DIR
    #print 'Temp Dir: ', TEMP_DIR
    #print 'Server: ', UPDATE_SERVER_URL
    #print 'User: ', UPDATE_SERVER_USER
    #print 'Password: ', UPDATE_SERVER_PWD
    #print 'Base Path: ', UPDATE_SERVER_PATH
    
    update_application()
