# Imports ----------------------------------------------------------------------
#--Standard
import os
import re
import string
import struct
import StringIO
import sys
import types

#--Local
import mosh
from mosh import _
import mush

#------------------------------------------------------------------------------
class Callables:
    """A singleton set of objects (typically functions or class instances) that 
    can be called as functions from the command line. 
    
    Functions are called with their arguments, while object instances are called 
    with their method and then their functions. E.g.:
    * bish afunction arg1 arg2 arg3
    * bish anInstance.aMethod arg1 arg2 arg3"""

    #--Ctor
    def __init__(self):
        """Initialization."""
        self.callObjs = {}

    #--Add a callable
    def add(self,callObj,callKey=None):
        """Add a callable object. 
        
        callObj:
            A function or class instance. 
        callKey: 
            Name by which the object will be accessed from the command line. 
            If callKey is not defined, then callObj.__name__ is used."""
        callKey = callKey or callObj.__name__
        self.callObjs[callKey] = callObj

    #--Help
    def help(self,callKey):
        """Print help for specified callKey."""
        help(self.callObjs[callKey])

    #--Main
    def main(self):
        callObjs = self.callObjs
        #--Call key, tail
        callParts  = string.split(sys.argv[1],'.',1)
        callKey    = callParts[0]
        callTail   = (len(callParts) > 1 and callParts[1])
        #--Help request?
        if callKey == '-h':
            help(self)
            return
        #--Not have key?
        if callKey not in callObjs:
            print "Unknown function/object:", callKey
            return
        #--Callable
        callObj = callObjs[callKey]
        if type(callObj) == types.StringType:
            callObj = eval(callObj)
        if callTail:
            callObj = eval('callObj.'+callTail)
        #--Args
        args = sys.argv[2:]
        #--Keywords?
        keywords = {}
        argDex = 0
        reKeyArg  = re.compile(r'^\-(\D\w+)')
        reKeyBool = re.compile(r'^\+(\D\w+)')
        while argDex < len(args):
            arg = args[argDex]
            if reKeyArg.match(arg):
                keyword = reKeyArg.match(arg).group(1)
                value   = args[argDex+1]
                keywords[keyword] = value
                del args[argDex:argDex+2]
            elif reKeyBool.match(arg):
                keyword = reKeyBool.match(arg).group(1)
                keywords[keyword] = 1
                del args[argDex]
            else:
                argDex = argDex + 1
        #--Apply
        apply(callObj,args,keywords)
#--Callables Singleton
callables = Callables()

def mainFunction(func):
    """A function for adding functions to callables."""
    callables.add(func)
    return func

#ETXT =========================================================================
etxtHeader = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2//EN">
<HTML>
<HEAD>
<META HTTP-EQUIV="CONTENT-TYPE" CONTENT="text/html; charset=iso-8859-1">
<TITLE>%s</TITLE>
<STYLE>
H2 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #c6c63c; font-family: "Arial", serif; font-size: 12pt; page-break-before: auto; page-break-after: auto }
H3 { margin-top: 0in; margin-bottom: 0in; border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: none; border-right: none; padding: 0.02in 0in; background: #e6e64c; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
H4 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-size: 10pt; font-style: normal; page-break-before: auto; page-break-after: auto }
H5 { margin-top: 0in; margin-bottom: 0in; font-family: "Arial", serif; font-style: italic; page-break-before: auto; page-break-after: auto }
P { margin-top: 0.01in; margin-bottom: 0.01in; font-family: "Arial", serif; font-size: 10pt; page-break-before: auto; page-break-after: auto }
P.list-1 { margin-left: 0.15in; text-indent: -0.15in }
P.list-2 { margin-left: 0.3in; text-indent: -0.15in }
P.list-3 { margin-left: 0.45in; text-indent: -0.15in }
P.list-4 { margin-left: 0.6in; text-indent: -0.15in }
P.list-5 { margin-left: 0.75in; text-indent: -0.15in }
P.list-6 { margin-left: 1.00in; text-indent: -0.15in }
.date0 { background-color: #FFAAAA }
.date1 { background-color: #ffc0b3 }
.date2 { background-color: #ffd5bb }
.date3 { background-color: #ffeac4 }
</STYLE>
</HEAD>
<BODY BGCOLOR='#ffffcc'>
"""

@mainFunction
def etxtToHtml(inFileName):
    import time
    """Generates an html file from an etxt file."""
    #--Re's
    reHead2 = re.compile(r'## *([^=]*) ?=*')
    reHead3 = re.compile(r'# *([^=]*) ?=*')
    reHead4 = re.compile(r'@ *(.*)\s+')
    reHead5 = re.compile(r'% *(.*)\s+')
    reList = re.compile(r'( *)([-!?\.\+\*o]) (.*)')
    reBlank = re.compile(r'\s+$')
    reMDash = re.compile(r'--')
    reBoldEsc = re.compile(r'\_')
    reBoldOpen = re.compile(r' _')
    reBoldClose = re.compile(r'(?<!\\)_( |$)')
    reItalicOpen = re.compile(r' ~')
    reItalicClose = re.compile(r'~( |$)')
    reBoldicOpen = re.compile(r' \*')
    reBoldicClose = re.compile(r'\*( |$)')
    reBold = re.compile(r'\*\*([^\*]+)\*\*')
    reItalic = re.compile(r'\*([^\*]+)\*')
    reLink = re.compile(r'\[\[(.*?)\]\]')
    reHttp = re.compile(r' (http://[_~a-zA-Z0-9\./%-]+)')
    reWww = re.compile(r' (www\.[_~a-zA-Z0-9\./%-]+)')
    reDate = re.compile(r'\[([0-9]+/[0-9]+/[0-9]+)\]')
    reContents = re.compile(r'\[CONTENTS=?(\d+)\]\s*$')
    reWd = re.compile(r'\W\d*')
    rePar = re.compile(r'\^(.*)')
    reFullLink = re.compile(r'(:|#|\.[a-zA-Z]{3,4}$)')
    #--Date styling (Replacement function used with reDate.)
    dateNow = time.time()
    def dateReplace(maDate):
        date = time.mktime(time.strptime(maDate.group(1),'%m/%d/%Y')) #[1/25/2005]
        age= int((dateNow-date)/(7*24*3600))
        if age < 0: age = 0
        if age > 3: age = 3
        return '<span class=date%d>%s</span>' % (age,maDate.group(1))
    def linkReplace(maLink):
        address = text = maLink.group(1).strip()
        if '|' in text:
            (address,text) = [chunk.strip() for chunk in text.split('|',1)]
        if not reFullLink.search(address):
            address = address+'.html'
        return '<a href="%s">%s</a>' % (address,text)
    #--Defaults
    title = ''
    level = 1
    spaces = ''
    headForm = "<h%d><a name='%s'>%s</a></h%d>\n"
    #--Open files
    inFileRoot = re.sub('\.[a-zA-Z]+$','',inFileName)
    inFile = open(inFileName)
    #--Init
    outLines = []
    contents = []
    addContents = 0
    #--Read through inFile
    for line in inFile.readlines():
        maHead2 = reHead2.match(line)
        maHead3 = reHead3.match(line)
        maHead4 = reHead4.match(line)
        maHead5 = reHead5.match(line)
        maPar   = rePar.match(line)
        maList  = reList.match(line)
        maBlank = reBlank.match(line)
        maContents = reContents.match(line)
        #--Contents
        if maContents:
            if maContents.group(1):
                addContents = int(maContents.group(1))
            else:
                addContents = 100
        #--Header 2?
        if maHead2:
            text = maHead2.group(1)
            name = reWd.sub('',text)
            line = headForm % (2,name,text,3)
            if addContents: contents.append((2,name,text))
            #--Title?
            if not title: title = text
        #--Header 3?
        elif maHead3:
            text = maHead3.group(1)
            name = reWd.sub('',text)
            line = headForm % (3,name,text,3)
            if addContents: contents.append((3,name,text))
            #--Title?
            if not title: title = text
        #--Header 4?
        elif maHead4:
            text = maHead4.group(1)
            name = reWd.sub('',text)
            line = headForm % (4,name,text,4)
            if addContents: contents.append((4,name,text))
        #--Header 5?
        elif maHead5:
            text = maHead5.group(1)
            name = reWd.sub('',text)
            line = headForm % (5,name,text,5)
            if addContents: contents.append((5,name,text))
        #--List item
        elif maList:
            spaces = maList.group(1)
            bullet = maList.group(2)
            text = maList.group(3)
            if bullet == '.': bullet = '&nbsp;'
            elif bullet == '*': bullet = '&bull;'
            level = len(spaces)/2 + 1
            line = spaces+'<p class=list-'+`level`+'>'+bullet+'&nbsp; '
            line = line + text + '\n'
        #--Paragraph
        elif maPar:
            line = '<p>'+maPar.group(1)
        #--Blank line
        elif maBlank:
            line = spaces+'<p class=list'+`level`+'>&nbsp;</p>'
        #--Misc. Text changes
        line = reMDash.sub('&#150',line)
        line = reMDash.sub('&#150',line)
        #--New bold/italic subs
        line = reBoldOpen.sub(' <B>',line)
        line = reItalicOpen.sub(' <I>',line)
        line = reBoldicOpen.sub(' <I><B>',line)
        line = reBoldClose.sub('</B> ',line)
        line = reBoldEsc.sub('_',line)
        line = reItalicClose.sub('</I> ',line)
        line = reBoldicClose.sub('</B></I> ',line)
        #--Old style bold/italic subs
        line = reBold.sub(r'<B><I>\1</I></B>',line)
        line = reItalic.sub(r'<I>\1</I>',line)
        #--Date
        line = reDate.sub(dateReplace,line)
        #--Local links
        line = reLink.sub(linkReplace,line)
        #--Hyperlink
        line = reHttp.sub(r' <a href="\1">\1</a>',line)
        line = reWww.sub(r' <a href="http://\1">\1</a>',line)
        #--Write it
        #print line
        outLines.append(line)
    inFile.close()
    #--Output file
    outFile = open(inFileRoot+'.html','w')
    outFile.write(etxtHeader % (title,))
    didContents = False
    for line in outLines:
        if reContents.match(line):
            if not didContents:
                baseLevel = min([level for (level,name,text) in contents])
                for (level,name,text) in contents:
                    level = level - baseLevel + 1
                    if level <= addContents:
                        outFile.write('<p class=list-%d>&bull;&nbsp; <a href="#%s">%s</a></p>\n' % (level,name,text))
                didContents = True
        else:
            outFile.write(line)
    outFile.write('</body>\n</html>\n')
    outFile.close()
    #--Done

@mainFunction
def genHtml(fileName):
    """Generate html from old style etxt file or from new style wtxt file."""
    ext = os.path.splitext(fileName)[1].lower()
    if  ext == '.etxt':
        etxtToHtml(fileName)
    elif ext == '.txt':
        import wtxt
        docsDir = r'c:\program files\bethesda softworks\morrowind\data files\docs'
        wtxt.genHtml(fileName,cssDir=docsDir)
    else:
        raise "Unrecognized file type: "+ ext

# Translation -----------------------------------------------------------------
@mainFunction
def getTranslatorName():
    """Prints locale."""
    import locale
    language = locale.getlocale()[0].split('_',1)[0]
    print "Your translator file is: Mopy\\locale\\%s.txt" % (language,)

@mainFunction
def dumpTranslator():
    """Dumps new translation key file using existing key, value pairs."""
    #--Locale Path
    import locale
    language = locale.getlocale()[0].split('_',1)[0]
    outPath = 'locale\\NEW%s.txt' % (language,)
    outFile = open(outPath,'w')
    #--Scan for keys and dump to 
    keyCount = 0
    dumpedKeys = set()
    reKey = re.compile(r'_\([\'\"](.+?)[\'\"]\)')
    for pyFile in ('mush.py','mosh.py','mash.py','masher.py'):
        pyText = open(pyFile)
        for lineNum,line in enumerate(pyText):
            line = re.sub('#.*','',line)
            for key in reKey.findall(line):
                if key in dumpedKeys: continue
                outFile.write('=== %s, %d\n' % (pyFile,lineNum+1))
                outFile.write(key+'\n>>>>\n')
                value = _(re.sub(r'\\n','\n',key))
                value = re.sub('\n',r'\\n',value)
                if value != key:
                    outFile.write(value)
                outFile.write('\n')
                dumpedKeys.add(key)
                keyCount += 1
        pyText.close()
    outFile.close()
    print keyCount,'translation keys written to',outPath

# Testing ---------------------------------------------------------------------
def init(initLevel):
    """Initializes mosh environment to specified level.
    initLevels:
        0: Settings
        1: mwInit File
        2: modInfos
        3: saveInfos"""
    #--Settings
    mosh.initSettings()
    mwDir = mosh.settings['mwDir']
    #--MwIniFile (initLevel >= 1)
    if initLevel < 1: return
    mosh.mwIniFile = mosh.MWIniFile(mwDir)
    mosh.mwIniFile.refresh()
    #--ModInfos (initLevel >= 2)
    if initLevel < 2: return
    mosh.modInfos = mosh.ModInfos(os.path.join(mwDir,'Data Files'))
    mosh.modInfos.refresh()
    #--SaveInfos (initLevel >= 3)
    if initLevel < 3: return
    mosh.saveInfos = mosh.SaveInfos(os.path.join(mwDir,'Saves'))
    mosh.saveInfos.refresh()

def tes3Hedr_testWrite(fileName):
    """Does a read write test on TES3 records."""
    init(3)
    if fileName in mosh.modInfos:
        fileInfo = mosh.modInfos[fileName]
    else:
        fileInfo = mosh.saveInfos[fileName]
    #--Mark as changed
    oldData = fileInfo.tes3.hedr.data
    fileInfo.tes3.hedr.changed = True

@mainFunction
def fileRefs_testWrite(fileName):
    """Does a read write test on cells."""
    init(3)
    fileRefs = mosh.FileRefs(mosh.saveInfos[fileName])
    fileRefs.refresh()
    for cell in fileRefs.cells:
        cellId = cell.getId()
        oldData = cell.data
        cell.changed = True
        cell.getSize()
        if cell.data != oldData:
            print cellId, 'BAD'
        else:
            #print cellId, "GOOD"
            pass

# Information -----------------------------------------------------------------
@mainFunction
def refInfo(fileName,forMods=-1,forCellId=None):
    """Prints reference info for specified file."""
    init(3)
    forMods = int(forMods)
    fileInfo = mosh.modInfos.data.get(fileName) or mosh.saveInfos.data.get(fileName)
    if not fileInfo: raise 'No such file: '+fileName
    masters = fileInfo.tes3.masters
    fileRefs = mosh.FileRefs(fileInfo,True)
    fileRefs.refresh()
    for cell in sorted(fileRefs.cells, cmp=lambda a,b: a.cmpId(b)):
        if forCellId and forCellId != cell.getId(): continue
        printCell = cell.getId()
        objects = cell.getObjects().list()
        objects.sort(key=lambda a: a[1])
        for object in objects:
            if forMods != -1 and forMods != object[0]: continue
            if printCell: 
                print printCell
                printCell = False
            master = object[0] and masters[object[0]-1][0]
            print ' ', object[:3], master

# Misc. -----------------------------------------------------------------------
#--Library Generator
@mainFunction
def genLibrary(modName,textName):
    init(2)
    fileInfo = mosh.modInfos[modName]
    fileLib = mosh.FileLibrary(fileInfo)
    fileLib.loadUI()
    fileLib.doImport(textName)
    fileLib.safeSave()

#--Schedule Generator
@mainFunction
def genSchedule(fileName,espName=None):
    generator = mosh.ScheduleGenerator()
    generator.loadText(fileName)
    #--Write to text file?
    if not espName:
        outName = os.path.splitext(fileName)[0]+'.mws'
        generator.dumpText(outName)
    #--Write to esp file?
    else:
        init(2)
        fileInfo = mosh.modInfos.data.get(espName)
        if not fileInfo: raise _('No such file: ')+espName
        generator.save(fileInfo)

#--Fix fix operator.
@mainFunction
def fixFix(fileName):
    """Search and replace change on scripts and dialog scripts.
    Strips spaces from around fix (->) operator."""
    rePointer = re.compile(r' -> ?',re.M)
    init(2)
    fileInfo = mosh.modInfos[fileName]
    #--Fix scripts
    if True:
        fileRep = mosh.FileRep(fileInfo)
        fileRep.loadUI(factory={'SCPT':mosh.Scpt})
        for script in fileRep.indexed['SCPT'].values():
            oldCode = script.sctx.data
            if rePointer.search(oldCode):
                newCode = rePointer.sub('->',oldCode)
                script.setCode(newCode)
                print script.id
        fileRep.safeSave()
    #--Fix dialog scripts
    if True:
        fileDials = mosh.FileDials(fileInfo)
        fileDials.load()
        for dial in fileDials.dials:
            for info in dial.infos:
                for record in info.records:
                    if record.name != 'BNAM': continue
                    if rePointer.search(record.data):
                        print dial.id
                        print ' ',info.text
                        print ' ',record.data
                        print
                        record.setData(rePointer.sub('->',record.data))
                        info.setChanged()
                        break
        fileDials.safeSave()

# Edit Plus Text Editors ------------------------------------------------------
def lcvNightSort():
    """TextMunch: Sort LCV evening/night schedule cells, ignoring sleep state setting."""
    import sys
    lines = sys.stdin.readlines()
    for line in lines:
        line = re.sub('@ night','@ evening',line)
        line = re.sub(r'[\*\+] \.','^ .',line)
        print line,
    for line in lines:
        print line,

@mainFunction
def pcLeveler(fileName):
    """TextMunch: Reads in 0/30 level settings and spits out a level setting script."""
    #--Constants
    import sys
    reSpace = re.compile(r'\s+')
    charSet0 = string.Template(mush.charSet0)
    charSet1 = string.Template(mush.charSet1)
    statNames = ('Agility', 'Block', 'Light Armor', 'Marksman', 'Sneak', 'Endurance', 'Heavy Armor', 'Medium Armor', 'Spear', 'Intelligence', 'Alchemy', 'Conjuration', 'Enchant', 'Security', 'Personality', 'Illusion', 'Mercantile', 'Speechcraft', 'Speed', 'Athletics', 'Hand To Hand', 'Short Blade', 'Unarmored', 'Strength', 'Acrobatics', 'Armorer', 'Axe', 'Blunt Weapon', 'Long Blade', 'Willpower', 'Alteration', 'Destruction', 'Mysticism', 'Restoration', 'Luck',)
    statGroups = (
        ('Primary',mush.primaryAttributes),
        ('Secondary',('Health',)),
        ('Combat Skills',mush.combatSkills),
        ('Magic Skills',mush.magicSkills),
        ('Stealth Skills',mush.stealthSkills))
    #--Read file/stdin
    if fileName:
        inFile = open(fileName)
    else:
        inFile = sys.stdin
    #--Read file
    stats = {}
    className = inFile.readline().strip()
    for statName, line in zip(statNames,inFile.readlines()[:35]):
        v00,v30 = re.match('(\d+)\s+(\d+)',line).groups()
        stats[statName] = (int(v00),int(v30))
        #print statName, stats[statName]
    inFile.close()
    #--Health
    str00,str30 = stats['Strength']
    end00,end30 = stats['Endurance']
    hea00 = (str00 + end00)/2
    hea30 = (str30 + end30)/2 + end30*29/10
    stats['Health'] = (hea00,hea30)
    #--Dump Script
    print charSet0.substitute(className=className)
    for tag,statNames in statGroups:
        print ';--'+tag
        for statName in statNames:
            compName = reSpace.sub('',statName)
            v00,v30 = stats[statName]
            if v00 == v30:
                print 'set%s %d' % (compName,v00,)
            else:
                print '  set stemp to %d + ((%d - %d)*level/30)' % (v00,v30,v00)
                print 'set%s stemp' % (compName,)
        print 
    print charSet1.substitute(className=className)

@mainFunction
def etxtToWtxt(fileName=None):
    """TextMunch: Converts etxt files to wtxt formatting."""
    if fileName:
        ins = open(fileName)
    else:
        import sys
        ins = sys.stdin
    for line in ins:
        line = re.sub(r'^\^ ?','',line)
        line = re.sub(r'^## ([^=]+) =',r'= \1 ==',line)
        line = re.sub(r'^# ([^=]+) =',r'== \1 ',line)
        line = re.sub(r'^@ ',r'=== ',line)
        line = re.sub(r'^% ',r'==== ',line)
        line = re.sub(r'\[CONTENTS=(\d+)\]',r'{{CONTENTS=\1}}',line)
        line = re.sub(r'~([^ ].+?)~',r'~~\1~~',line)
        line = re.sub(r'_([^ ].+?)_',r'__\1__',line)
        line = re.sub(r'\*([^ ].+?)\*',r'**\1**',line)
        print line,

@mainFunction
def textMunch(fileName=None):
    """TextMunch: This is a standin for EditPlus Text munching. It should just 
    call whatever text muncher is currently being used."""
    etxtToWtxt(fileName)
 
# Temp ------------------------------------------------------------------------
#--Temp
@mainFunction
def temp(fileName):
    init(2)
    fileInfo = mosh.modInfos[fileName]
    fileDials = mosh.FileDials(fileInfo)
    fileDials.load(factory={'INFO':mosh.Info})
    #--Replacement defs
    repls = {
        'activator':'init',
        'allowBack':'back',
        'aShort': 's01',
        'bShort': 's02',
        }
    replKeys = set(repls.keys())
    reRepls = re.compile(r'\b('+('|'.join(replKeys))+r')\b')
    reStartScript = re.compile('^startScript',re.I+re.M)
    def doRepl(mo):
        return repls[mo.group(0)]
    #--Loop over dials
    for dial in fileDials.dials:
        print dial.id
        for info in dial.infos:
            #--Change id?
            if info.spId == 'wr_mysMenu_s':
                info.spId = 'wr_mysCre'
                info.setChanged()
            elif info.spId == 'wr_bookMenu_s':
                info.spId = 'wr_bookCre'
                info.setChanged()
            #--Change tests?
            if info.spId in ('wr_mysCre','wr_bookCre'): 
                #--Test vars
                for index,test in enumerate(info.tests):
                    if not test:
                        pass
                    elif test.text.lower() == 'modder':
                        if test.value == 0 and test.oper == 0:
                            test.text = 'menu'
                            test.value = -1
                            print ' modder >> menu'
                        else:
                            info.tests[index] = 0
                            print ' modder X'
                    elif test.text in replKeys:
                        print '',test.text,repls[test.text]
                        test.text = repls[test.text]
                #--Result
                if info.script:
                    newScript = reRepls.sub(doRepl,info.script)
                    newScript = reStartScript.sub('player->startScript',newScript)
                    if newScript != info.script:
                        info.script = newScript
                        print ' script subbed'
                info.setChanged()
    fileDials.safeSave()

#--Temp 2
@mainFunction
def temp2(fileName=None):
    init(2)
    fileName = fileName or 'Wrye CharSet.esp'
    csi = mosh.CharSetImporter()
    csi.loadText("Wrye CharSets.etxt")
    csi.printMajors()
    #csi.save(mosh.modInfos[fileName])

# Main -------------------------------------------------------------------------
if __name__ == '__main__':
    callables.main()
