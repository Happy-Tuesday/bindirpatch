import os
import subprocess
import sys

#SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SEVENZIP_EXE = os.path.join('.', '7zip', 'x64', '7za.exe')
BSDIFF_EXE = os.path.join('.', 'bsdiff', 'bsdiff.exe')
BSPATCH_EXE = os.path.join('.', 'bsdiff', 'bspatch.exe')


def get_stdout(silent):
    if silent:
        return open(os.devnull, 'wb')
    else:
        return None


def bsdiff(oldFile, newFile, patchFile, silent=False):
    """Creates a binary diff between <oldFile> and <newFile> and stores it in <patchFile>"""
    subprocess.call([BSDIFF_EXE, oldFile, newFile, patchFile], stdout=get_stdout(silent))

def bspatch(oldFile, newFile, patchFile, silent=False):
    """Applies the <patchFile> to the <oldFile> and writes the result to <newFile>"""
    subprocess.call([BSPATCH_EXE, oldFile, newFile, patchFile], stdout=get_stdout(silent))


def zip_directory(directory, zipPath, silent=False):
    """Creates a 7z archive at <zipPath> containing the files from <directory>."""
    subprocess.call([SEVENZIP_EXE, 'a', zipPath, directory, '-mx9', '-t7z'], stdout=get_stdout(silent))
    
def unzip_directory(zipPath, directory, silent=False):
    """Extracts the 7z archive <zipPath> and puts the content into directory <directory>"""
    subprocess.call([SEVENZIP_EXE, 'x', zipPath, '-o' + directory], stdout=get_stdout(silent))


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


class Progress:
    def __init__(self, total, dots):
        self.total = total
        self.current = 0
        self.dotsPrinted = 0
        self.dotsMax = dots

    def print_header(self, numSegments=1):
        sys.stdout.write('[')
        dotsPerSegment = self.dotsMax / numSegments
        for i in range(0, self.dotsMax):
            if (i+1) % dotsPerSegment == 0:
                sys.stdout.write('|')
            else:
                sys.stdout.write(' ')
        sys.stdout.write(']\n ')
        
    def set_progress(self, progress):
        if progress <= self.current:
            return

        self.current = progress
        percentage = progress / float(self.total)
        nextDotPercentage = (self.dotsPrinted + 1) / float(self.dotsMax)
        if percentage >= nextDotPercentage:
            sys.stdout.write('.')
            self.dotsPrinted += 1
        if self.current >= self.total:
            print ''
            
    def add_progress(self, progress):
        self.set_progress(self.current + progress)
