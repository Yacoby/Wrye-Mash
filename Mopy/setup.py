# -*- coding: cp1252 -*-
from distutils.core import setup

# py2exe stuff
import py2exe, os, sys, imp, glob

#-# retrieving wx install dir for getting gdiplus.dll
wxDlls = ["gdiplus.dll"]
import wx
wxDir = os.path.split(wx.__file__)[0]
del wx
wxDlls = [os.path.join(wxDir, a) for a in wxDlls]
#-#


msvcppath = os.path.join(os.path.expandvars('%WINDIR%'), 'winsxs', '*', 'msvcp90.dll')
msvcrpath = os.path.join(os.path.expandvars('%WINDIR%'), 'winsxs', '*', 'msvcr90.dll')
msvcDlls = glob.glob(msvcppath) + glob.glob(msvcrpath)

dest_folder = "..\\bin\\Mopy"

## Building up the distributable 'utils.dcg'
f = open(os.path.join("mash", "utils.dcg"), "r")
utils_org = f.read()
f.close()
utils_dcg = """; utils.dcg
; File containing the mash utils data
;
; Format of a file entry
;
; name of the utility; command line to launch the utility; parameters; description of the utility
"""
f = open("utils.dcg", "w")
f.write(utils_dcg)
f.close()

#if you are building this you may need to change the public key for the dll files
#in can be found in the manifest files in %windir%\winsxs\
manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
	version="5.0.0.0"
	processorArchitecture="x86"
	name="%(prog)s"
	type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
	<dependentAssembly>
		<assemblyIdentity
			type="win32"
			name="Microsoft.Windows.Common-Controls"
			version="6.0.0.0"
			processorArchitecture="X86"
			publicKeyToken="6595b64144ccf1df"
			language="*"
		/>
	</dependentAssembly>
</dependency>
<dependency>
    <dependentAssembly>
    <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.21022.8"
            processorArchitecture="x86"
            publicKeyToken="1fc8b3b9a1e18e3b"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24


for a in sys.argv[1:]:
	if a not in ['-q', 'py2exe']:
		sys.argv.remove(a)
if "-q" not in sys.argv:
	sys.argv.append("-q")
if "py2exe" not in sys.argv:
	sys.argv.append("py2exe")

prog_resources = ['7z.exe',
                  '7z.dll',
                  'mash_default.ini',
                  'Wrye Mash.html',
                  'content.html',
                  'Wrye Mash.txt',
                  'readme.txt',
                  'utils.dcg'] + wxDlls + msvcDlls

## Remove the old 'build' folder
if os.access('.\\build', os.F_OK):
	print 'Deleting old build folder...'
	for root, dirs, files in os.walk('.\\build', topdown=False):
		for name in files:
			os.remove(os.path.join(root, name))
		for name in dirs:
			os.rmdir(os.path.join(root, name))
			
	os.rmdir('.\\build')

class Target:
	def __init__(self, **kw):
		self.__dict__.update(kw)
		# for the versioninfo resources
		self.version = '84.0.0.1'
		self.company_name = "Wrye & D.C.-G."
		self.copyright = "Wrye 2009 (see 'Wrye Mash.txt' for full credits) & D.C.-G. 2009/2010"
		self.name = "WryeMash"

# includes for py2exe
includes=["wx", "encodings", "encodings.utf_8"]
excludes=["Tkconstants","Tkinter","tcl"]

opts = { 'py2exe': { 'includes':includes,
                     'excludes':excludes,
                     "packages": ['wx.lib.pubsub'], 
                     'dll_excludes': ['msvcp90.dll'],
			         "compressed": 1,
                     "optimize": 2,
                     "ascii": 1,
                     "bundle_files": 1,
                     "dist_dir":dest_folder} }
# end of py2exe stuff

prog = Target(
	description='Morrowind mod organizer and tools.',
	author="Wrye (see 'Wrye Mash.txt' for full credits)",
	script='mash.py',
	icon_resources=[(0,".\\images\\Wrye Mash.ico")],
	other_resources = [(RT_MANIFEST, 1, manifest_template % dict(prog="WryeMash"))],
	)

setup(
	data_files=[('.',prog_resources)],
	zipfile = None,
	windows=[prog],
	options=opts
	)

from distutils import dir_util
dir_util.copy_tree('..\\Data Files', '..\\bin\\Data Files')
folds = ['Data','Extras','images','locale']
for fold in folds:
	dir_util.copy_tree(fold, dest_folder+'\\%s'%fold)

## Restoring original 'utils.dcg'
f = open(os.path.join("mash", "utils.dcg"), "w")
f.write(utils_org)
f.close()


#compress if required
if os.path.exists('upx.exe'):
    files = ( glob.glob(os.path.join(dest_folder, '*.dll'))
            + glob.glob(os.path.join(dest_folder, '*.exe')) )
    #note, --ultra-brute takes ages.
    #If you want a fast build change it to --best
    args = ['upx.exe', '--ultra-brute'] + files
    os.spawnv(os.P_WAIT, 'upx.exe', args)
