import os
import subprocess

import conf

def run(args):
    startupinfo = None
    if os.name == 'nt':
        info = subprocess.STARTUPINFO()
        #WIN32 constant: STARTUPINFO.STARTF_USESHOWWINDOW
        info.dwFlags |= 0x00000001
    p = subprocess.Popen(args,
                         executable=getLocation(),
                         cwd=getDataDir(),
                         startupinfo=info,
                         stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE) 
    return p.communicate()

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

def fixit(hideBackups=True, backupDir=None):
    args = ['tes3cmd.exe', 'fixit']

    if hideBackups:
        args += ['--hide-backups']

    if backupDir:
        args += ['--backup-dir', backupDir]

    return run(args)

def clean(files, replace=False, hideBackups=True, backupDir=None):
    args = ['tes3cmd.exe', 'clean']

    if replace:
        args += ['--replace']

    if hideBackups:
        args += ['--hide-backups']

    if backupDir:
        args += ['--backup-dir', backupDir]

    args += files
    return run(args)
