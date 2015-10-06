import os
import sys
import shutil
from ftplib import FTP

import bindirpatch
from utils import find_application_version, zip_directory

OLD_DIR = None
NEW_DIR = None
TEMP_DIR = None
OUT_DIR = None
UPDATE_SERVER_URL = None
UPDATE_SERVER_USER = None
UPDATE_SERVER_PWD = None
UPDATE_SERVER_PATH = None

def deploy():
    #increment_version()
    #clear_temp_dir()
    #create_patch()
    #zip_full_game()
    upload()

def increment_version():
    print 'incrementing version'
    oldVersion = find_application_version(OLD_DIR)
    versionFileName = os.path.join(NEW_DIR, 'VERSION')
    with open(versionFileName, 'w') as versionFile:
        versionFile.write(str(oldVersion+1))

def clear_temp_dir():
    print 'cleaning temp dir'
    if os.path.exists(TEMP_DIR):
        os.rename(TEMP_DIR, TEMP_DIR + '_deleteme')
        shutil.rmtree(TEMP_DIR + '_deleteme')
    os.makedirs(TEMP_DIR)

def create_patch():
    print 'creating patch'
    tmpFile = bindirpatch.create_patch(OLD_DIR, NEW_DIR, TEMP_DIR)
    newVersion = find_application_version(NEW_DIR)
    outFile = os.path.join(OUT_DIR, 'patches', 'v' + str(newVersion))
    os.rename(tmpFile, outFile)

def zip_full_game():
    print 'zipping game'
    outFile = os.path.join(OUT_DIR, 'latest.7z')
    zip_directory(NEW_DIR, outFile)

def upload():
    print 'Connecting to Server...'
    print UPDATE_SERVER_USER + ' ' + UPDATE_SERVER_PWD + ' ' + UPDATE_SERVER_PATH
    ftp = FTP(UPDATE_SERVER_URL)
    ftp.login(UPDATE_SERVER_USER, UPDATE_SERVER_PWD)
    ftp.cwd(UPDATE_SERVER_PATH)

    print 'Uploading full game...'
    fullGamePath = os.path.join(OUT_DIR, 'latest.7z')
    #with open(fullGamePath, 'rb') as f:
        #ftp.storbinary('STOR latest', f)

    print 'Uploading patch...'
    version = find_application_version(NEW_DIR)
    patchPath = os.path.join(OUT_DIR, 'patches', 'v' + str(version))
    with open(patchPath, 'rb') as f:
        ftp.cwd('patches')
        ftp.storbinary('STOR v' + str(version), f)

    ftp.quit()
    print 'Upload Complete'


def parseExtraArgs(i):
    if len(sys.argv) <= i:
        return
    arg = sys.argv[i]
    
    if arg.startswith('-j'):
        bindirpatch.NUM_WORKERS = int(arg[2:])

    else:
        print 'Invalid argument: ' + sys.argv[i]
        usage()
        
    parseExtraArgs(i+1)
    

def usage():
    print 'Usage: python deploy.py <oldDir> <newDir> <tempDir> <outDir> <url> <user> <password> <remotePath> [options]'
    print '  oldDir: last uploaded build (current latest build on server)'
    print '  newDir: build to be deployed'
    print '  tempDir: Where to put temp files. This directory will be deleted!'
    print '  outDir: where to put the result files'
    print '  url: url of the ftp server'
    print '  user: username for uploading on the server'
    print '  password: password for ftp user'
    print '  remotePath: path on the ftp server to store the files'
    print ''
    print 'Options:'
    print ' -j#     Jobs, sets number of worker processes for patch building, ex: -j4'
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 9:
        usage()

    OLD_DIR = sys.argv[1]
    NEW_DIR = sys.argv[2]
    TEMP_DIR = sys.argv[3]
    OUT_DIR = sys.argv[4]
    UPDATE_SERVER_URL = sys.argv[5]
    UPDATE_SERVER_USER = sys.argv[6]
    UPDATE_SERVER_PWD = sys.argv[7]
    UPDATE_SERVER_PATH = sys.argv[8]
    print 'Update server path: ' + UPDATE_SERVER_PATH
        
    parseExtraArgs(9)
    deploy()
