#!/usr/bin/python
import os
import sys
import shutil
import filecmp
import subprocess
import zlib
import multiprocessing

"""
    Directory-wide diff and patch.
    Patch files are 7z archives containing an index file and a files directory.
    The index file has a list of modified files. Each entry consists of an operation
    (A/M/D = Added/Modified/Deleted), the Adler32 checksums of the old and the new version
    and the relative path to the file.
    The files directory contains all added files and, for all modified files, the bsdiff
    patches that can convert the old to the new version. The directory structure within
    the files directory is the same as in the target directory.

    Creating a patch can be multithreaded to make use of multiple cpu cores.
    To avoid conflicts, each process writes to its own index file, they are merged at the end.

    Requires the command-line version of 7zip and the Windows version of bsdiff/bspatch.
"""

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SEVENZIP_EXE = os.path.join(SCRIPT_DIR, '7zip', 'x64', '7za.exe')
BSDIFF_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bsdiff.exe')
BSPATCH_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bspatch.exe')
VERBOSITY_LEVEL = 0
NUM_WORKERS = 1

def create_patch(oldDir, newDir, outDir):
    patchDir = os.path.join(outDir, 'patch_temp')
    if not os.path.exists(patchDir):
        os.mkdir(patchDir)
    elif not is_empty_directory(patchDir):
        print 'patch_temp directory is not empty! Aborting.'
        return False
    
    if validate_environment():
        walk_old_dir(oldDir, newDir, patchDir)
        walk_new_dir(oldDir, newDir, patchDir)
        merge_index(patchDir)
        zip_directory(patchDir, patchDir + '.7z')


def apply_patch(patchFilePath, targetDir):
    baseDir = os.path.dirname(patchFilePath)
    patchDir = os.path.join(baseDir, 'patch_temp')
    if validate_environment():
        unzip_directory(patchFilePath, os.path.dirname(patchDir))
        index = read_index(patchDir)
        for (operation, path, checksumOld, checksumNew) in index:
            if (operation != 'A'):
                validate_checksum_pre(os.path.join(targetDir, path), checksumOld)
        for (operation, path) in index:
            apply_file_operation(operation, path, patchDir, targetDir)
        for (operation, path, checksumOld, checksumNew) in index:
            if (operation != 'D'):
                validate_checksum_post(os.path.join(targetDir, path), checksumNew)

    shutil.rmtree(patchDir)


def apply_file_operation(operation, relPath, patchDir, targetDir):
    srcPath = os.path.join(patchDir, 'files', relPath)
    dstPath = os.path.join(targetDir, relPath)
    
    if operation == 'A':
        add_file(srcPath, dstPath)
    if operation == 'M':
        modify_file(srcPath, dstPath)
    if operation == 'D':
        delete_file(dstPath)


def walk_dir(rootPath, oldDir, newDir, patchDir):
    indexPath = os.path.join(patchDir, 'index')
    for (dirpath, dirnames, filenames) in os.walk(rootPath):
        relDir = os.path.relpath(dirpath, rootPath)
        for filename in filenames:
            relPath = os.path.join(relDir, filename)
            oldPath = os.path.join(oldDir, relPath)
            newPath = os.path.join(newDir, relPath)
            patchPath = os.path.join(patchDir, 'files', relPath)
            yield (relPath, oldPath, newPath, patchPath, indexPath)


def walk_old_dir(oldDir, newDir, patchDir):
    """Traverse <oldDir> and index all files that are modified or deleted in <newDir>"""
    print ''
    print 'Checking Old Files in ' + oldDir
    if NUM_WORKERS > 1:
        pool = multiprocessing.Pool(processes=NUM_WORKERS)
        pool.map(visit_old_file, walk_dir(oldDir, oldDir, newDir, patchDir))
    else:
        map(visit_old_file, walk_dir(oldDir, oldDir, newDir, patchDir))

def visit_old_file((relPath, oldPath, newPath, patchPath, indexPath)):
    print_verbose(2, '    ' + oldPath)

    if not os.path.exists(newPath):
        add_to_index('D', relPath, indexPath)
        return

    if not filecmp.cmp(oldPath, newPath):
        mkdir_if_not_exists(os.path.dirname(patchPath))
        bsdiff(oldPath, newPath, patchPath)
        chkOld = checksum(oldPath)
        chkNew = checksum(newPath)
        add_to_index('M', relPath, indexPath, chkOld, chkNew)
        return
    

def walk_new_dir(oldDir, newDir, patchDir):
    """Traverse <newDir> and index all files as added that don't appear in <oldDir>"""
    print 'Checking for new files...'
    for (relPath, oldPath, newPath, patchPath, indexPath) in walk_dir(newDir, oldDir, newDir, patchDir):
        visit_new_file(relPath, oldPath, newPath, patchPath, indexPath)


def visit_new_file(relPath, oldPath, newPath, patchPath, indexPath):
        print_verbose(2, '    ' + relPath)
        if not os.path.exists(oldPath):
            targetDir = os.path.dirname(patchPath)
            mkdir_if_not_exists(targetDir)
            shutil.copy(newPath, targetDir)
            add_to_index('A', relPath, indexPath)


def add_file(srcPath, dstPath):
    dstDir = os.path.dirname(dstPath)
    if not os.path.exists(dstDir):
        os.makedirs(dstDir)
    os.rename(srcPath, dstPath)

def modify_file(filePath, patchFile):
    bspatch(filePath, filePath, patchFile)

def delete_file(path):
    os.remove(path)


def bsdiff(oldFile, newFile, patchFile):
    """Creates a binary diff between <oldFile> and <newFile> and stores it in <patchFile>"""
    global BSDIFF_EXE
    subprocess.call([BSDIFF_EXE, oldFile, newFile, patchFile])

def bspatch(oldFile, newFile, patchFile):
    """Applies the <patchFile> to the <oldFile> and writes the result to <newFile>"""
    global BSPATCH_EXE
    subprocess.call([BSPATCH_EXE, oldFile, newFile, patchFile])


def add_to_index(operation, path, indexPath, checksumOld=0, checksumNew=0):
    """Adds an entry to the index. Each process has its own index file.
        They must be merged with merge_index() after all processes are done."""
    indexPath = indexPath + '.' + str(os.getpid())
    line = operation + ' ' + str(checksumOld) + ' ' + str(checksumNew) + ' ' + path
    print_verbose(1, line)
    with open(indexPath, 'a') as indexFile:
        indexFile.write(unicode(line + '\n'))

def merge_index(patchDir):
    """Merges the index files of the separate worker processes into one."""
    indexFiles = [ os.path.join(patchDir,f) \
                       for f in os.listdir(patchDir) \
                           if os.path.isfile(os.path.join(patchDir,f)) \
                           and f.startswith('index.') ]
    indexFile = os.path.join(patchDir, 'index')
    with open(indexFile, 'w') as index:
        for partialIndexFile in indexFiles:
            with open(partialIndexFile, 'r') as partialIndex:
                index.write(partialIndex.read())
            os.remove(partialIndexFile)

def read_index(patchDir):
    """Read and parse the index file. Returns a list of
        (operation, path, checksumOld, checksumNew) tuples"""
    indexPath = os.path.join(patchDir, 'index')
    with open(indexPath, 'r') as indexFile:
        result = []
        for line in indexFile.readlines():
            parts = line.split(4)
            operation = parts[0]
            checksumOld = int(parts[1])
            checksumNew = int(parts[2])
            path = parts[3]
            result.append( (operation, path, checksumOld, checksumNew) )
    return result


def zip_directory(directory, zipPath):
    """Creates a 7z archive at <zipPath> containing the files from <directory>."""
    global SEVENZIP_EXE
    subprocess.call([SEVENZIP_EXE, 'a', zipPath, directory, '-mx9', '-t7z'])
    
def unzip_directory(zipPath, directory):
    """Extracts the 7z archive <zipPath> and puts the content into directory <directory>"""
    global SEVENZIP_EXE
    subprocess.call([SEVENZIP_EXE, 'x', zipPath, '-o' + directory])


def checksum(path):
    with open(path, 'r') as f:
        return zlib.adler32(f.read())

class ChecksumException(Exception):
    def __init__(self, path):
        self.path = path

    def msg(self):
        return 'Cannot apply patch because file at ' + self.path + \
            ' does not have the correct checksum. Please reinstall the full release.'


def validate_checksum_pre(path, expectedChecksum):
    if checksum(path) != expectedChecksum:
        raise ChecksumException(path)

def validate_checksum_post(path, expectedChecksum):
    if checksum(path) != expectedChecksum:
        print 'WARNING: File ' + path + ' is corrupted! Please reinstall the full release.'


def validate_environment():
    global BSDIFF_EXE
    global BSPATCH_EXE
    global SEVENZIP_EXE
    if not os.path.exists(BSDIFF_EXE):
        print "Couldn't find bsdiff"
        print "Please download from http://sites.inka.de/tesla/download/bsdiff4.3-win32.zip"
        return False
    if not os.path.exists(BSPATCH_EXE):
        print "Couldn't find bspatch"
        print "Please download from http://sites.inka.de/tesla/download/bsdiff4.3-win32.zip"
        return False
    if not os.path.exists(SEVENZIP_EXE):
        print "Couldn't find 7zip"
        print "Please download from http://www.7-zip.org/a/7z1507-extra.7z"
        return False
    
    return True


def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            if not os.path.exists(path):
                raise Exception("cannot create directory " + path)
        

def is_empty_directory(path):
    if not os.path.isdir(path):
        return False
    if len(os.listdir(path)) > 0:
        return False
    return True


def print_verbose(verbosity, msg):
    if verbosity <= VERBOSITY_LEVEL:
        print msg


def _parseExtraArgs(i):
    global VERBOSITY_LEVEL
    global NUM_WORKERS
    if i < len(sys.argv):
        if sys.argv[i] == '-v':            
            VERBOSITY_LEVEL = 1
            print 'Verbosity Level ' + str(VERBOSITY_LEVEL)
        elif sys.argv[i] == '-vv':
            VERBOSITY_LEVEL = 2
            print 'Verbosity Level ' + str(VERBOSITY_LEVEL)
        elif sys.argv[i][0:2] == '-j':
            NUM_WORKERS = int(sys.argv[i][2:])
            print 'Workers: ' + str(NUM_WORKERS)
        else:
            print 'unrecognized argument ' + sys.argv[i]
            usage()
        _parseExtraArgs(i+1)

def parseExtraArgs(i):
    _parseExtraArgs(i)
    if VERBOSITY_LEVEL > 0 and NUM_WORKERS > 1:
        print 'WARNING: There will be no verbose log output when using multiple workers.'

def usage():
    print 'Wrong arguments. Usage:'
    print '    patch.py diff <oldDir> <newDir> <outDir> [switch args]'
    print 'or'
    print '    patch.py patch <patchFile> <targetDir> [switch args]'
    print ''
    print 'Switch Args: '
    print '-v   Print more status messages'
    print '-vv  Print a lot of status messages (only for debugging)'
    print '-j#  Parallel processing. Replace # with the number of desired worker threads'
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()

    operation = sys.argv[1]
    if operation == 'diff':
        if len(sys.argv) < 5:
            usage()
        oldDir = sys.argv[2]
        newDir = sys.argv[3]
        patchDir = sys.argv[4]
        parseExtraArgs(5)
        create_patch(oldDir, newDir, patchDir)
        
    elif operation == 'patch':
        if len(sys.argv) < 4:
            usage()
        patchFile = sys.argv[2]
        targetDir = sys.argv[3]
        parseExtraArgs(4)
        apply_patch(patchFile, targetDir)
    else:
        usage()
