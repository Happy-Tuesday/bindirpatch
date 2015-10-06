import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SEVENZIP_EXE = os.path.join(SCRIPT_DIR, '7zip', 'x64', '7za.exe')
BSDIFF_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bsdiff.exe')
BSPATCH_EXE = os.path.join(SCRIPT_DIR, 'bsdiff', 'bspatch.exe')


def bsdiff(oldFile, newFile, patchFile):
    """Creates a binary diff between <oldFile> and <newFile> and stores it in <patchFile>"""
    subprocess.call([BSDIFF_EXE, oldFile, newFile, patchFile])

def bspatch(oldFile, newFile, patchFile):
    """Applies the <patchFile> to the <oldFile> and writes the result to <newFile>"""
    subprocess.call([BSPATCH_EXE, oldFile, newFile, patchFile])


def zip_directory(directory, zipPath):
    """Creates a 7z archive at <zipPath> containing the files from <directory>."""
    subprocess.call([SEVENZIP_EXE, 'a', zipPath, directory, '-mx9', '-t7z'])
    
def unzip_directory(zipPath, directory):
    """Extracts the 7z archive <zipPath> and puts the content into directory <directory>"""
    subprocess.call([SEVENZIP_EXE, 'x', zipPath, '-o' + directory])


def find_application_version(projectDir):
    versionFilePath = os.path.join(projectDir, 'VERSION')
    try:
        with open(versionFilePath, 'r') as versionFile:
            versionStr = versionFile.read()
            return int(versionStr)

    except ValueError:
        print 'Invalid Version: "' + versionStr + '"'
        return None

    except IOError:
        print 'Could not open VERSION file at ' + versionFilePath
        return None
