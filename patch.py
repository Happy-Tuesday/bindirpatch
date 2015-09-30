#!/usr/bin/python
import os
import sys
import shutil
import filecmp
import subprocess
import zlib

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SEVENZIP_EXE = os.path.join(SCRIPT_DIR, '7zip', 'x64', '7za.exe')
BSDIFF_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bsdiff.exe')
BSPATCH_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bspatch.exe')
VERBOSITY_LEVEL = 0

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
        zip_directory(patchDir, patchDir + '.7z')


def apply_patch(patchFilePath, targetDir):
    baseDir = os.path.dirname(patchFilePath)
    patchDir = os.path.join(baseDir, 'patch_temp')
    if validate_environment():
        unzip_directory(patchFilePath, os.path.dirname(patchDir))
        index = read_index(patchDir)
        for (operation, path, checksumOld, checksumNew) in index:
            if (operation != 'A'):
                validate_checksum(os.path.join(targetDir, path), checksumOld)
        for (operation, path) in index:
            apply_file_operation(operation, path, patchDir, targetDir)
        for (operation, path, checksumOld, checksumNew) in index:
            if (operation != 'D'):
                validate_checksum(os.path.join(targetDir, path), checksumNew)

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



def walk_old_dir(oldDir, newDir, patchDir):
    print ''
    print 'Checking Old Files in ' + oldDir
    indexPath = os.path.join(patchDir, 'index')
    for (dirpath, dirnames, filenames) in os.walk(oldDir):
        relDir = os.path.relpath(dirpath, oldDir)
        for filename in filenames:
            relPath = os.path.join(relDir, filename)
            oldPath = os.path.join(oldDir, relPath)
            newPath = os.path.join(newDir, relPath)
            patchPath = os.path.join(patchDir, 'files', relPath)
            print_verbose(2, '    ' + oldPath)

            if not os.path.exists(newPath):
                add_to_index('D', relPath, indexPath)
                continue

            if not filecmp.cmp(oldPath, newPath):
                mkdir_if_not_exists(os.path.dirname(patchPath))
                bsdiff(oldPath, newPath, patchPath)
                chkOld = checksum(oldPath)
                chkNew = checksum(newPath)
                add_to_index('M', relPath, indexPath, chkOld, chkNew)
                continue


def walk_new_dir(oldDir, newDir, patchDir):
    print 'Checking for new files...'
    indexPath = os.path.join(patchDir, 'index')
    for (dirpath, dirnames, filenames) in os.walk(newDir):
        relDir = os.path.relpath(dirpath, newDir)
        for filename in filenames:
            relPath = os.path.join(relDir, filename)
            oldPath = os.path.join(oldDir, relPath)
            newPath = os.path.join(newDir, relPath)
            patchPath = os.path.join(patchDir, 'files', relPath)
            print_verbose(2, '    ' + relPath)

            if not os.path.exists(oldPath):
                patchDir = os.path.dirname(patchPath)
                mkdir_if_not_exists(patchDir)
                shutil.copy(newPath, patchDir)
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
    global BSDIFF_EXE
    subprocess.call([BSDIFF_EXE, oldFile, newFile, patchFile])

def bspatch(oldFile, newFile, patchFile):
    global BSPATCH_EXE
    subprocess.call([BSPATCH_EXE, oldFile, newFile, patchFile])


def add_to_index(operation, path, indexPath, checksumOld=0, checksumNew=0):
    line = operation + ' ' + str(checksumOld) + ' ' + str(checksumNew) + ' ' + path
    print_verbose(1, line)
    with open(indexPath, 'a') as indexFile:
        indexFile.write(line + '\n')

def read_index(patchDir):
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
    global SEVENZIP_EXE
    subprocess.call([SEVENZIP_EXE, 'a', zipPath, directory, '-mx9', '-t7z'])
    
def unzip_directory(zipPath, directory):
    global SEVENZIP_EXE
    subprocess.call([SEVENZIP_EXE, 'x', zipPath, '-o' + directory])


def checksum(path):
    with open(path, 'r') as f:
        return zlib.adler32(f.read())


def validate_environment():
    global BSDIFF_EXE
    global BSPATCH_EXE
    global SEVENZIP_EXE
    if not os.path.exists(BSDIFF_EXE):
        print "Couldn't find bsdiff"
        return False
    if not os.path.exists(BSPATCH_EXE):
        print "Couldn't find bspatch"
        return False
    if not os.path.exists(SEVENZIP_EXE):
        print "Couldn't find 7zip"
        return False
    
    return True


def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        

def is_empty_directory(path):
    if not os.path.isdir(path):
        return False
    if len(os.listdir(path)) > 0:
        return False
    return True


def print_verbose(verbosity, msg):
    if verbosity <= VERBOSITY_LEVEL:
        print msg


def parseExtraArgs(i):
    global VERBOSITY_LEVEL
    if i < len(sys.argv):
        if sys.argv[i] == '-v':            
            VERBOSITY_LEVEL = 1
            print 'Verbosity Level ' + str(VERBOSITY_LEVEL)
        elif sys.argv[i] == '-vv':
            VERBOSITY_LEVEL = 2
            print 'Verbosity Level ' + str(VERBOSITY_LEVEL)
        else:
            print 'unrecognized argument ' + sys.argv[i]
            usage()
        parseExtraArgs(i+1)

def usage():
    print 'Wrong arguments. Usage:'
    print '    patch.py diff <oldDir> <newDir> <outDir> [-v | -vv]'
    print 'or'
    print '    patch.py patch <patchFile> <targetDir> [-v | -vv]'
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
