import os
import subprocess
import threading
import time
import Queue as queue

from .. import conf


class HelperMixin:
    def getSubprocess(self, args):
        startupinfo = None

        #hides the command promp on NT systems
        if os.name == 'nt':
            info = subprocess.STARTUPINFO()
            #WIN32 constant: STARTUPINFO.STARTF_USESHOWWINDOW
            info.dwFlags |= 0x00000001

        return subprocess.Popen(args,
                             executable=getLocation(),
                             cwd=getDataDir(),
                             startupinfo=info,
                             stderr=subprocess.PIPE,
                             stdout=subprocess.PIPE) 
    
    def buildFixitArgs(self, hideBackups, backupDir):
        args = ['tes3cmd.exe', 'fixit']
        if hideBackups:
            args.append('--hide-backups')
        if backupDir:
            args += ['--backup-dir', backupDir]
        return args

    def buildCleanArgs(self, files, replace, hideBackups, backupDir,
                       cells, dups, gmsts, instances, junk):

        if not (cells or dups or gmsts or instances or junk):
            raise Exception('No options selected')

        args = ['tes3cmd.exe', 'clean']
        if replace:
            args.append('--replace')
        if hideBackups:
            args.append('--hide-backups')
        if backupDir:
            args += ['--backup-dir', backupDir]

        #if everything is true then we don't need to set any of the options
        if cells and dups and gmsts and instances and junk:
            args += files
            return args

        if cells:
            args.append('--cell-params')
        if dups:
            args.append('--dups')
        if gmsts:
            args.append('--gmsts')
        if instances:
            args.append('--instances')
        if junk:
            args.append('--junk-cells')

        args += files
        return args

    def buildHeaderArgs(self, file, hideBackups, backupDir, sync, 
                        updateMasters, updateRecordCount):
        args = ['tes3cmd.exe', 'header']
        if hideBackups:
            args.append('--hide-backups')
        if backupDir:
            args += ['--backup-dir', backupDir]

        if sync:
            args.append('--synchronize')
        if updateMasters:
            args.append('--update-masters')
        if updateRecordCount:
            args.append('--update-record-count')
        args.append(file)
        return args


class Basic(HelperMixin):
    def fixit(self, hideBackups=True, backupDir=None):
        args = self.buildFixitArgs(hideBackups, backupDir)
        self.out, self.err = self.getSubprocess(args).communicate()

class Threaded(threading.Thread, HelperMixin):
    """ A class that manages a Threaded process in another thread """

    def __init__(self, callback=None):
        """
        The callback should be a function that sends the done event to your
        application. It should be constructed with care as it is called in this
        thread not the main one.
        """
        threading.Thread.__init__(self)
        self.msg = queue.Queue()
        self.callback = callback
        self.err = self.out = ''

    def stop(self):
        """
        Stops the execution of the thread. You must join the thread after
        calling this as it isn't instant. This is safe to call from another thread
        """
        self.msg.put('STOP')

    def fixit(self, hideBackups=True, backupDir=None):
        self.args = self.buildFixitArgs(hideBackups, backupDir)
        self.start()

    def clean(self, files, replace=False, hideBackups=True, backupDir=None,
              cells=True, dups=True, gmsts=True, instances=True, junk=True):
        self.files = files
        self.args = self.buildCleanArgs(files, replace, hideBackups, backupDir,
                                        cells, dups, gmsts, instances, junk) 
        self.start()

    def header(self, file, hideBackups=True, backupDir=None, sync=True,
               updateMasters=False, updateRecordCount=False):
        self.files = [file]
        self.args = self.buildHeaderArgs(file, hideBackups, backupDir, sync,
                                         updateMasters, updateRecordCount)
        self.start()

    def run(self):
        """
        This shouldn't be called directly, use a function like clean
        that correctly sets the state
        """
        p = self.getSubprocess(self.args)

        while p.poll() is None:
            if not self.msg.empty():
                msg = self.msg.get()
                if msg == 'STOP':
                    p.terminate()
                    return
            time.sleep(0.01)

        for line in iter(p.stdout.readline,''):
            self.out += line.strip() + '\n'

        for line in iter(p.stderr.readline,''):
            self.err += line.strip() + '\n'

        if self.callback:
            self.callback()


def getDataDir():
    cwd = os.getcwd()
    mwdir = os.path.dirname(cwd)
    return os.path.join(mwdir, 'Data Files')

def getLocation():
    location = None
    cwd = os.getcwd()
    locs = [cwd,
            os.path.join(cwd, 'tes3cmd'),
            conf.settings['mwDir'],
            os.path.join(conf.settings['mwDir'], 'Data Files')]
    for loc in locs:
        path = os.path.join(loc, 'tes3cmd.exe')
        if os.path.exists(path):
            return path
    return None
