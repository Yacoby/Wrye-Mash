# -*- coding: cp1252 -*-
from distutils.core import setup

# py2exe stuff
import py2exe, os, sys, imp

#-# retrieving wx install dir for getting msvcp71.dll and gdiplus.dll
wxDlls = ("MSVCP71.dll","gdiplus.dll")
import wx
wxDir = os.path.split(wx.__file__)[0]
del wx
wxDlls = [os.path.join(wxDir, a) for a in wxDlls]
#-#

dest_folder = "..\\bin\\Mopy"

## Building up the distributable 'utils.dcg'
f = open("utils.dcg", "r")
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

prog_resources = ['7z.exe','7z.dll','mash_default.ini','Wrye Mash.html','content.html','Wrye Mash.txt','readme.txt', 'sources.zip',
				'utils.dcg'] + wxDlls

## Remove the old 'build' folder
if os.access('.\\build', os.F_OK):
	print 'Deleting old build folder...'
	for root, dirs, files in os.walk('.\\build', topdown=False):
		for name in files:
			os.remove(os.path.join(root, name))
		for name in dirs:
			os.rmdir(os.path.join(root, name))
			
	os.rmdir('.\\build')

## Source archive construction
if os.access('sources.zip', os.F_OK) == True:
	os.remove('sources.zip')
os.system('7z a -r -x!@excludes.txt sources.zip @includes.txt')

class Target:
	def __init__(self, **kw):
		self.__dict__.update(kw)
		# for the versioninfo resources
		self.version = '84.0.0.1'
		self.company_name = "Wrye & D.C.-G."
		self.copyright = "Wrye 2009 (see 'Wrye Mash.txt' for full credits) & D.C.-G. 2009/2010"
		self.name = "WryeMash"

# includes for py2exe
includes=["wx", "encodings"]
excludes=["Tkconstants","Tkinter","tcl"]

opts = { 'py2exe': { 'includes':includes,
                     'excludes':excludes,
						"compressed": 1,
						"optimize": 2,
						"ascii": 1,
						#"xref":1,
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
f = open("utils.dcg", "w")
f.write(utils_org)
f.close()
