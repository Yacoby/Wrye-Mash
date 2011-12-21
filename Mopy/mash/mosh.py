# -*- coding: cp1252 -*-
#
# Modified by D.C.-G. < 16:35 2010-06-11 >
#
# Modifications for UtilsPanel extension.
#
# Notes:
#
# mush is imported several times : first as global module, then in functions as local module.
# Is it realy necessary ?
#
#------------------------------------------------------------------------------
#
# Localization ----------------------------------------------------------------
#--Not totally clear on this, but it seems to safest to put locale first...
import locale; locale.setlocale(locale.LC_ALL,'')
#locale.setlocale(locale.LC_ALL, 'German') #--Language test
import time

def formatInteger(value):
    """Convert integer to string formatted to locale."""
    return locale.format('%d',int(value),1)

def formatDate(value):
    """Convert time to string formatted to to locale's default date/time."""
    return time.strftime('%c',time.localtime(value))

# Imports ---------------------------------------------------------------------
#--Python
import array
import cPickle
import cStringIO
import ConfigParser
import copy
import math
import os
import re
import shutil
import string
import struct
import sys
import stat

import bolt
from bolt import BoltError
from bolt import LString, GPath, Flags, DataDict, SubProgress

import compat

import mush
bush = mush #--Cheap code compatibility.

# Singletons, Constants -------------------------------------------------------
#--File Singletons
mwIniFile = None #--MWIniFile singleton
modInfos  = None  #--ModInfos singleton
saveInfos = None #--SaveInfos singleton

#--Settings
dirs = {}
settings  = None

#--Default settings
settingDefaults = {
    'mosh.modInfos.resetMTimes': 0,
    'mosh.modInfos.objectMaps': r'Mash\ObjectMaps.pkl',
    'mosh.fileInfo.backupDir': r'Mash\Backups',
    'mosh.fileInfo.hiddenDir': r'Mash\Hidden',
    'mosh.fileInfo.snapshotDir': r'Mash\Snapshots',
    }

# Locale: String Translation --------------------------------------------------
def compileTranslator(txtPath,pklPath):
    """Compiles specified txtFile into pklFile."""
    reSource = re.compile(r'^=== ')
    reValue = re.compile(r'^>>>>\s*$')
    reBlank = re.compile(r'^\s*$')
    reNewLine = re.compile(r'\\n')
    #--Scan text file
    translator = {}
    def addTranslation(key,value):
        key   = reNewLine.sub('\n',key[:-1])
        value = reNewLine.sub('\n',value[:-1])
        if key and value:
            translator[key] = value
    key,value,mode = '','',0
    textFile = file(txtPath)
    for line in textFile:
        #--Blank line. Terminates key, value pair
        if reBlank.match(line):
            addTranslation(key,value)
            key,value,mode = '','',0
        #--Begin key input?
        elif reSource.match(line):
            addTranslation(key,value)
            key,value,mode = '','',1
        #--Begin value input?
        elif reValue.match(line):
            mode = 2
        elif mode == 1:
            key += line
        elif mode == 2:
            value += line
    addTranslation(key,value) #--In case missed last pair
    textFile.close()
    #--Write translator to pickle
    filePath = pklPath
    tempPath = filePath+'.tmp'
    cPickle.dump(translator,open(tempPath,'w'))
    if os.path.exists(filePath): os.remove(filePath)
    os.rename(tempPath,filePath)
    
#--Do translator test and set
language = locale.getlocale()[0].split('_',1)[0]
languagePkl, languageTxt = (os.path.join('locale',language+ext) for ext in ('.pkl','.txt'))
#--Recompile pkl file?
if os.path.exists(languageTxt) and (
    not os.path.exists(languagePkl) or (
        os.path.getmtime(languageTxt) > os.path.getmtime(languagePkl)
        )
    ):
    compileTranslator(languageTxt,languagePkl)
#--Use dictionary from pickle as translator
if os.path.exists(languagePkl):
    pklFile = open(languagePkl)
    _translator = cPickle.load(pklFile)
    pklFile.close()
    def _(text): return _translator.get(text,text)
else:
    def _(text): return text

# Exceptions ------------------------------------------------------------------
class MoshError(Exception):
    """Generic Error"""
    def __init__(self,message):
        self.message = message
    def __str__(self):
        return self.message

# Coding Errors ---------------------------------------------------------------
class AbstractError(MoshError): 
    """Coding Error: Abstract code section called."""
    def __init__(self,message=_('Abstract section called.')):
        MoshError.__init__(self,message)

class ArgumentError(MoshError):
    """Coding Error: Argument out of allowed range of values."""
    pass

class StateError(MoshError):
    """Error: Object is corrupted."""
    pass

class UncodedError(MoshError): 
    """Coding Error: Call to section of code that hasn't been written."""
    def __init__(self,message=_('Section is not coded yet.')):
        MoshError.__init__(self,message)

# TES3 File Errors ------------------------------------------------------------
class Tes3Error(MoshError):
    """TES3 Error: File is corrupted."""
    def __init__(self,inName,message):
        MoshError.__init__(self,message)
        self.inName = inName

    def __str__(self):
        if self.inName:
            return self.inName+': '+self.message
        else:
            return _('Unknown File: ')+self.message

class Tes3ReadError(Tes3Error):
    """TES3 Error: Attempt to read outside of buffer."""
    def __init__(self,inName,recType,tryPos,maxPos):
        self.recType = recType
        self.tryPos = tryPos
        self.maxPos = maxPos
        if tryPos < 0:
            message = (_('%s: Attempted to read before (%d) beginning of file/buffer.')
                % (recType,tryPos))
        else:
            message = (_('%s: Attempted to read past (%d) end (%d) of file/buffer.') %
                (recType,tryPos,maxPos))
        Tes3Error.__init__(self,inName,message)

class Tes3RefError(Tes3Error):
    """TES3 Error: Reference is corrupted."""
    def __init__(self,inName,cellId,objId,iObj,iMod,masterName=''):
        self.cellId = cellId
        self.iMod = iMod
        self.iObj = iObj
        self.objId = objId
        self.masterName = masterName
        message = (_('%s: Bad Ref: %s: objId: %s iObj: %d') % 
            (inName,cellId,objId,iObj))
        if iMod:
            message += ' iMod: %d [%s]' % (iMod,masterName)
        Tes3Error.__init__(self,inName,message)

class Tes3SizeError(Tes3Error):
    """TES3 Error: Record/subrecord has wrong size."""
    def __init__(self,inName,recName,readSize,maxSize,exactSize=True):
        self.recName = recName
        self.readSize = readSize
        self.maxSize = maxSize
        self.exactSize = exactSize
        if exactSize:
            messageForm = _('%s: Expected size == %d, but got: %d ')
        else:
            messageForm = _('%s: Expected size <= %d, but got: %d ')
        Tes3Error.__init__(self,inName,messageForm % (recName,readSize,maxSize))


class Tes3UnknownSubRecord(Tes3Error):
    """TES3 Error: Unknown subrecord."""
    def __init__(self,inName,subName,recName):
        Tes3Error.__init__(self,inName,_('Extraneous subrecord (%s) in %s record.') 
            % (subName,recName))

# Usage Errors ----------------------------------------------------------------
class MaxLoadedError(MoshError):
    """Usage Error: Attempt to add a mod to load list when load list is full."""
    def __init__(self,message=_('Load list is full.')):
        MoshError.__init__(self,message)

# Data Dictionaries -----------------------------------------------------------
#------------------------------------------------------------------------------
class Settings:
    """Settings dictionary. Changes are saved to pickle file."""
    def __init__(self,path='settings.pkl'):
        """Initialize. Read settings from pickle file."""
        self.path = path
        self.changed = []
        self.deleted = []
        self.data = {}
        #--Load
        if os.path.exists(self.path):
            inData = compat.uncpickle(open(self.path))
            self.data.update(inData)

    def loadDefaults(self,defaults):
        """Add default settings to dictionary. Will not replace values that are already set."""
        for key in defaults.keys():
            if key not in self.data:
                self.data[key] = defaults[key]

    def save(self):
        """Save to pickle file. Only key/values marked as changed are saved."""
        #--Data file exists?
        filePath = self.path
        if os.path.exists(filePath):
            ins = open(filePath)
            outData = compat.uncpickle(ins)
            ins.close()
            #--Delete some data?
            for key in self.deleted:
                if key in outData:
                    del outData[key]
        else:
            outData = {}
        #--Write touched data
        for key in self.changed:
            outData[key] = self.data[key]
        #--Pickle it
        tempPath = filePath+'.tmp'
        cPickle.dump(outData,open(tempPath,'w'))
        renameFile(tempPath,filePath,True)

    def setChanged(self,key):
        """Marks given key as having been changed. Use if value is a dictionary, list or other object."""
        if key not in self.data:
            raise ArgumentError("No settings data for "+key)
        if key not in self.changed:
            self.changed.append(key)

    def getChanged(self,key,default=None):
        """Gets and marks as changed."""
        if default != None and key not in self.data:
            self.data[key] = default
        self.setChanged(key)
        return self.data.get(key)

    #--Dictionary Emulation
    def has_key(self,key):
        """Dictionary emulation."""
        return self.data.has_key(key)
    def get(self,key,default=None):
        """Dictionary emulation."""
        return self.data.get(key,default)
    def setdefault(self,key,default):
        """Dictionary emulation."""
        return self.data.setdefault(key,default)
    def __contains__(self,key):
        """Dictionary emulation."""
        return self.data.has_key(key)
    def __getitem__(self,key):
        """Dictionary emulation."""
        return self.data[key]
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        if key in self.deleted: self.deleted.remove(key)
        if key not in self.changed: self.changed.append(key)
        self.data[key] = value
    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        if key in self.changed: self.changed.remove(key)
        if key not in self.deleted: self.deleted.append(key)
        del self.data[key]

#------------------------------------------------------------------------------
class TableColumn:
    """Table accessor that presents table column as a dictionary."""
    def __init__(self,table,column):
        self.table = table
        self.column = column
    #--Dictionary Emulation
    def keys(self):
        """Dictionary emulation."""
        table = self.table
        column = self.column
        return [key for key in table.data.keys() if (column in table.data[key])]
    def has_key(self,key):
        """Dictionary emulation."""
        return self.__contains__(key)
    def clear(self):
        """Dictionary emulation."""
        self.table.delColumn(self.column)
    def get(self,key,default=None):
        """Dictionary emulation."""
        return self.table.getItem(key,self.column,default)
    def __contains__(self,key):
        """Dictionary emulation."""
        tableData = self.table.data
        return tableData.has_key(key) and tableData[key].has_key(self.column)
    def __getitem__(self,key):
        """Dictionary emulation."""
        return self.table.data[key][self.column]
    def __setitem__(self,key,value):
        """Dictionary emulation. Marks key as changed."""
        self.table.setItem(key,self.column,value)
    def __delitem__(self,key):
        """Dictionary emulation. Marks key as deleted."""
        self.table.delItem(key,self.column)

#------------------------------------------------------------------------------
class Table:
    """Simple data table of rows and columns, saved in a pickle file."""
    def __init__(self,path):
        """Intialize and read data from file, if available."""
        self.path = path
        self.data = {}
        self.hasChanged = False
        #--Load
        if os.path.exists(self.path):
            ins = open(self.path)
            inData = compat.uncpickle(ins)
            self.data.update(inData)

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            filePath = self.path
            tempPath = filePath+'.tmp'
            fileDir = os.path.split(filePath)[0]
            if not os.path.exists(fileDir): os.makedirs(fileDir)
            cPickle.dump(self.data,open(tempPath,'w'))
            renameFile(tempPath,filePath,True)
            self.hasChanged = False

    def getItem(self,row,column,default=None):
        """Get item from row, column. Return default if row,column doesn't exist."""
        data = self.data
        if row in data and column in data[row]:
            return data[row][column]
        else:
            return default

    def getColumn(self,column):
        """Returns a data accessor for column."""
        return TableColumn(self,column)

    def setItem(self,row,column,value):
        """Set value for row, column."""
        data = self.data
        if row not in data:
            data[row] = {}
        data[row][column] = value
        self.hasChanged = True

    def delItem(self,row,column):
        """Deletes item in row, column."""
        data = self.data
        if row in data and column in data[row]:
            del data[row][column]
            self.hasChanged = True

    def delRow(self,row):
        """Deletes row."""
        data = self.data
        if row in data:
            del data[row]
            self.hasChanged = True

    def delColumn(self,column):
        """Deletes column of data."""
        data = self.data
        for rowData in data.values():
            if column in rowData:
                del rowData[column]
                self.hasChanged = True

    def moveRow(self,oldRow,newRow):
        """Renames a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow]
            del data[oldRow]
            self.hasChanged = True

    def copyRow(self,oldRow,newRow):
        """Copies a row of data."""
        data = self.data
        if oldRow in data:
            data[newRow] = data[oldRow].copy()
            self.hasChanged = True

#------------------------------------------------------------------------------
class PickleDict(bolt.PickleDict):
    """Dictionary saved in a pickle file. Supports older bash pickle file formats."""
    def __init__(self,path,oldPath=None,readOnly=False):
        """Initialize."""
        bolt.PickleDict.__init__(self,path,readOnly)
        self.oldPath = oldPath or GPath('')

    def exists(self):
        """See if pickle file exists."""
        return (bolt.PickleDict.exists(self) or self.oldPath.exists())

    def load(self):
        """Loads vdata and data from file or backup file. 
        
        If file does not exist, or is corrupt, then reads from backup file. If 
        backup file also does not exist or is corrupt, then no data is read. If 
        no data is read, then self.data is cleared.

        If file exists and has a vdata header, then that will be recorded in 
        self.vdata. Otherwise, self.vdata will be empty.
        
        Returns: 
        0: No data read (files don't exist and/or are corrupt)
        1: Data read from file
        2: Data read from backup file
        """
        result = bolt.PickleDict.load(self)
        if not result and self.oldPath.exists():
            ins = None
            try:
                ins = self.oldPath.open('r')
                self.data.update(compat.uncpickle(ins))
                ins.close()
                result = 1
            except EOFError:
                if ins: ins.close()
        #--Done
        return result

    def save(self):
        """Save to pickle file."""
        saved = bolt.PickleDict.save(self)
        if saved:
            self.oldPath.remove()
            self.oldPath.backup.remove()
        return saved

# Util Functions --------------------------------------------------------------
# Common re's
#--Unix new lines
reUnixNewLine = re.compile(r'(?<!\r)\n')
reSaveFile = re.compile('\.ess$',re.I)
reModExt  = re.compile(r'\.es[mp](.ghost)?$',re.I)

#--Version number in tes3.hedr
reVersion = re.compile(r'^(Version:?) *([-0-9\.]*\+?) *\r?$',re.M)

#--Misc
reExGroup = re.compile('(.*?),')

#------------------------------------------------------------------------------
def cstrip(inString):
    """Convert c-string (null-terminated string) to python string."""
    zeroDex = inString.find('\x00')
    if zeroDex == -1:
        return inString
    else:
        return inString[:zeroDex]

def dictFromLines(lines,sep=None):
    """Generate a dictionary from a string with lines, stripping comments and skipping empty strings."""
    reComment = re.compile('#.*')
    temp = [reComment.sub('',x).strip() for x in lines.split('\n')]
    if sep == None or type(sep) == type(''):
        temp = dict([x.split(sep,1) for x in temp if x])
    else: #--Assume re object.
        temp = dict([sep.split(x,1) for x in temp if x])
    return temp

def getMatch(reMatch,group=0):
    """Returns the match or an empty string."""
    if reMatch: return reMatch.group(group)
    else: return ''

y2038Resets = []
def getmtime(path):
    """Returns mtime for path. But if mtime is outside of epoch, then resets mtime to an in-epoch date and uses that."""
    import random
    mtime = os.path.getmtime(path)
    #--Y2038 bug? (os.path.getmtime() can't handle years over unix epoch)
    if mtime <= 0:
        #--Kludge mtime to a random time within 10 days of 1/1/2037
        mtime = time.mktime((2037,1,1,0,0,0,3,1,0))
        mtime += random.randint(0,10*24*60*60) #--10 days in seconds
        os.utime(path,(time.time(),mtime))
        y2038Resets.append(os.path.basename(path))
    return mtime

def iff(bool,trueValue,falseValue):
    """Return true or false value depending on a boolean test."""
    if bool:
        return trueValue
    else:
        return falseValue

def invertDict(indict):
    """Invert a dictionary."""
    return dict([(y,x) for x,y in indict.items()])

def listFromLines(lines):
    """Generate a list from a string with lines, stripping comments and skipping empty strings."""
    reComment = re.compile('#.*')
    temp = [reComment.sub('',x).strip() for x in lines.split('\n')]
    temp = [x for x in temp if x]
    return temp

def listSubtract(alist,blist):
    """Return a copy of first list minus items in second list."""
    result = []
    for item in alist:
        if item not in blist:
            result.append(item)
    return result

def renameFile(oldPath,newPath,makeBack=False):
    """Moves file from oldPath to newPath. If newPath already exists then it 
    will either be moved to newPath.bak or deleted depending on makeBack."""
    if os.path.exists(newPath): 
        if makeBack:
            backPath = newPath+'.bak'
            if os.path.exists(backPath):
                os.remove(backPath)
            os.rename(newPath,backPath)
        else:
            os.remove(newPath)
    os.rename(oldPath,newPath)

def rgbString(red,green,blue):
    """Converts red, green blue ints to rgb string."""
    return chr(red)+chr(green)+chr(blue)

def rgbTuple(rgb):
    """Converts red, green, blue string to tuple."""
    return struct.unpack('BBB',rgb)

def winNewLines(inString):
    """Converts unix newlines to windows newlines."""
    return reUnixNewLine.sub('\r\n',inString)

# IO Wrappers -----------------------------------------------------------------
#------------------------------------------------------------------------------
class Log:
    """Log Callable. This is the abstract/null version. Useful version should 
    override write functions.
    
    Log is divided into sections with headers. Header text is assigned (through 
    setHeader), but isn't written until a message is written under it. I.e., 
    if no message are written under a given header, then the header itself is 
    never written."""

    def __init__(self):
        """Initialize."""
        self.header = None
        self.prevHeader = None
        self.indent = ''

    def setHeader(self,header):
        """Sets the header."""
        self.header = header

    def __call__(self,message):
        """Callable. Writes message, and if necessary, header and footer."""
        if self.header != self.prevHeader:
            if self.prevHeader:
                self.writeFooter()
            if self.header:
                self.writeHeader(self.header)
            self.prevHeader = self.header
        self.writeMessage(message)

    #--Abstract/null writing functions...
    def writeHeader(self,header):
        """Write header. Abstract/null version."""
        pass
    def writeFooter(self):
        """Write mess. Abstract/null version."""
        pass
    def writeMessage(self,message):
        """Write message to log. Abstract/null version."""
        pass

#------------------------------------------------------------------------------
class LogFile(Log):
    """Log that writes messages to file."""
    def __init__(self,out):
        self.out = out
        Log.__init__(self)

    def writeHeader(self,header):
        self.out.write(self.indent+header+'\n')

    def writeFooter(self):
        self.out.write(self.indent+'\n')

    def writeMessage(self,message):
        self.out.write(self.indent+message+'\n')

#------------------------------------------------------------------------------
class Progress:
    """Progress Callable: Shows progress on message change and at regular intervals."""
    def __init__(self,interval=0.5):
        self.interval = interval
        self.message = None
        self.time = 0
        self.base = 0.0
        self.scale = 1.0
        self.max = 1.0

    def setBaseScale(self,base=0.0,scale=1.0):
        if scale == 0: raise ArgumentError(_('Scale must not equal zero!'))
        self.base = base
        self.scale = scale
    
    def setMax(self,max):
        self.max = 1.0*max or 1.0 #--Default to 1.0

    def __call__(self,rawProgress,message=None):
        if not message: message = self.message
        if ((message != self.message) or 
            (time.time() > (self.time+self.interval))):
            self.doProgress(self.base+self.scale*rawProgress/self.max, message)
            self.message = message
            self.time = time.time()

    def doProgress(self,progress,message):
        """Default doProgress does nothing."""
        pass

#------------------------------------------------------------------------------
class ProgressFile(Progress):
    """Prints progress to file (stdout by default)."""
    def __init__(self,interval=0.5,out=None):
        Progress.__init__(self,interval)
        self.out = out

    def doProgress(self,progress,message):
        out = self.out or sys.stdout #--Defaults to stdout
        out.write('%0.2f %s\n' % (progress,message))

#------------------------------------------------------------------------------
class Tes3Reader:
    """Wrapper around an TES3 file in read mode. 
    Will throw a Tes3ReadError if read operation fails to return correct size."""
    def __init__(self,inName,ins):
        """Initialize."""
        self.inName = inName
        self.ins = ins
        #--Get ins size
        curPos = ins.tell()
        ins.seek(0,2)
        self.size = ins.tell()
        ins.seek(curPos)

    #--IO Stream ------------------------------------------
    def seek(self,offset,whence=0,recType='----'):
        """File seek."""
        if whence == 1:
            newPos = self.ins.tell()+offset
        elif whence == 2:
            newPos = self.size + offset
        else:
            newPos = offset
        if newPos < 0 or newPos > self.size: 
            raise Tes3ReadError(self.inName, recType,newPos,self.size)
        self.ins.seek(offset,whence)
    
    def tell(self):
        """File tell."""
        return self.ins.tell()

    def close(self):
        """Close file."""
        self.ins.close()
    
    def atEnd(self):
        """Return True if current read position is at EOF."""
        return (self.ins.tell() == self.size)

    #--Read/unpack ----------------------------------------
    def read(self,size,recType='----'):
        """Read from file."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise Tes3SizeError(self.inName, recType,endPos,self.size)
        return self.ins.read(size)
    
    def unpack(self,format,size,recType='-----'):
        """Read file and unpack according to struct format."""
        endPos = self.ins.tell() + size
        if endPos > self.size:
            raise Tes3ReadError(self.inName, recType,endPos,self.size)
        return struct.unpack(format,self.ins.read(size))

    def unpackRecHeader(self):
        """Unpack a record header."""
        return self.unpack('4s3i',16,'REC_HEAD')

    def unpackSubHeader(self,recType='----',expName=None,expSize=0):
        """Unpack a subrecord header. Optionally checks for match with expected name and size."""
        (name,size) = self.unpack('4si',8,recType+'.SUB_HEAD')
        #--Match expected name?
        if expName and expName != name:
            raise Tes3Error(self.inName,_('%s: Expected %s subrecord, but found %s instead.') 
                % (recType,expName,name))
        #--Match expected size?
        if expSize and expSize != size:
            raise Tes3SizeError(self.inName,recType+'.'+name,size,expSize,True)
        return (name,size)

    #--Find data ------------------------------------------
    def findSubRecord(self,subName,recType='----'):
        """Finds subrecord with specified name."""
        while not self.atEnd():
            (name,size) = self.unpack('4si',8,recType+'.SUB_HEAD')
            if name == subName:
                return self.read(size,recType+'.'+subName)
            else:
                self.seek(size,1,recType+'.'+name)
        #--Didn't find it?
        else:
            return None

#------------------------------------------------------------------------------
class Tes3Writer:
    """Wrapper around an TES3 output stream. Adds utility functions."""
    def __init__(self,out):
        """Initialize."""
        self.out = out

    #--Stream Wrapping
    def write(self,data):
        self.out.write(data)

    def getvalue(self):
        return self.out.getvalue()

    def close(self):
        self.out.close()

    #--Additional functions.
    def pack(self,format,*data):
        self.out.write(struct.pack(format,*data))

    def packSub(self,type,data,*values):
        """Write subrecord header and data to output stream.
        Call using either packSub(type,data), or packSub(type,format,values)."""
        if values: data = struct.pack(data,*values)
        self.out.write(struct.pack('4si',type,len(data)))
        self.out.write(data)

    def packSub0(self,type,data):
        """Write subrecord header and data + null terminator to output stream."""
        self.out.write(struct.pack('4si',type,len(data)+1))
        self.out.write(data)
        self.out.write('\x00')

# TES3 Abstract ---------------------------------------------------------------
#------------------------------------------------------------------------------
class SubRecord:
    """Generic Subrecord."""
    def __init__(self,name,size,ins=None,unpack=False):
        self.changed = False
        self.name = name
        self.size = size
        self.data = None 
        self.inName = ins and getattr(ins,'inName',None)
        if ins: self.load(ins,unpack)

    def load(self,ins,unpack=False):
        self.data = ins.read(self.size,'----.----')
    
    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def setData(self,data):
        """Sets data and size."""
        self.data = data
        self.size = len(data)

    def getSize(self):
        """Return size of self.data, after, if necessary, packing it."""
        if not self.changed: return self.size
        #--StringIO Object
        out = Tes3Writer(cStringIO.StringIO())
        self.dumpData(out)
        #--Done
        self.data = out.getvalue()
        data.close()
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        raise AbstractError
    
    def dump(self,out):
        if self.changed: raise StateError(_('Data changed: ')+ self.name)
        if not self.data: raise StateError(_('Data undefined: ')+self.name)
        out.write(struct.pack('4si',self.name,len(self.data)))
        out.write(self.data)

#------------------------------------------------------------------------------
class Record:
    """Generic Record."""
    def __init__(self,name,size,delFlag,recFlag,ins=None,unpack=False):
        self.changed = False
        self.name = name
        self.size = size
        self.delFlag = delFlag
        self.recFlag = recFlag
        self.data = None 
        self.id = None
        self.inName = ins and getattr(ins,'inName',None)
        if ins: self.load(ins,unpack)

    def load(self,ins=None,unpack=False):
        """Load data from ins stream or internal data buffer."""
        name = self.name
        #--Read, but don't analyze.
        if not unpack:
            self.data = ins.read(self.size,name)
        #--Read and analyze ins.
        elif ins:
            inPos = ins.tell()
            self.loadData(ins)
            ins.seek(inPos,0,name+'_REWIND')
            self.data = ins.read(self.size,name)
        #--Analyze internal buffer.
        else:
            reader = Tes3Reader(self.inName,cStringIO.StringIO(self.data))
            self.loadData(reader)
            reader.close()

    def loadData(self,ins):
        """Loads data from input stream. Called by load()."""
        raise AbstractError

    def setChanged(self,value=True):
        """Sets changed attribute to value. [Default = True.]"""
        self.changed = value

    def setData(self,data):
        """Sets data and size."""
        self.data = data
        self.size = len(data)

    def getSize(self):
        if self.changed: raise AbstractError
        return self.size

    def getSize(self):
        """Return size of self.data, after, if necessary, packing it."""
        if not self.changed: return self.size
        #--Pack data and return size.
        out = Tes3Writer(cStringIO.StringIO())
        self.dumpData(out)
        self.data = out.getvalue()
        out.close()
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

    def dumpData(self,out):
        """Dumps state into data. Called by getSize()."""
        raise AbstractError
    
    def dump(self,out):
        """Dumps record header and data into output file stream."""
        if self.changed: raise StateError(_('Data changed: ')+ self.name)
        if not self.data: raise StateError(_('Data undefined: ')+self.name)
        out.write(struct.pack('4s3i',self.name,self.size,self.delFlag,self.recFlag))
        out.write(self.data)

    def getId(self):
        """Get id. Doesn't work for all record types."""
        if getattr(self,'id',None):
            return self.id
        name = self.name
        #--Singleton records 
        if name in frozenset(('FMAP','GAME','JOUR','KLST','PCDT','REFR','SPLM','TES3')):
            return None
        #--Special records.
        elif name == 'CELL':
            reader = self.getReader()
            srName = reader.findSubRecord('NAME',name)
            srData = reader.findSubRecord('DATA',name)
            (flags,gridX,gridY) = struct.unpack('3i',record.data)
            if flags & 1:
                self.id = cstrip(srName)
            else:
                self.id = '[%d,%d]' % (gridX,gridY)
        elif name == 'INFO':
            srData = self.getReader().findSubRecord('INAM',name)
            self.id = cstrip(srData)
        elif name == 'LAND':
            srData = self.getReader().findSubRecord('INTV',name)
            self.id = '[%d,%d]' % struct.unpack('2i',srData)
        elif name == 'PGRD':
            reader = self.getReader()
            srData = reader.findSubRecord('DATA',name)
            srName = reader.findSubRecord('NAME',name)
            gridXY = struct.unpack('2i',srData[:8])
            if srData != (0,0) or not srName:
                self.id = '[%d,%d]' % gridXY
            else:
                self.id = cstrip(srName)
        elif name == 'SCPT':
            srData = self.getReader().findSubRecord('SCHD',name)
            self.id = cstrip(srData[:32])
        #--Most records: id in NAME record.
        else:
            srData = self.getReader().findSubRecord('NAME',name)
            self.id = srData and cstrip(srData)
        #--Done
        return self.id

    def getReader(self):
        """Returns a Tes3Reader wrapped around self.data."""
        return Tes3Reader(self.inName,cStringIO.StringIO(self.data))

# ------------------------------------------------------------------------------
class ContentRecord(Record):
    """Content record. Abstract parent for CREC, CNTC, NPCC record classes."""
    def getId(self):
        """Returns base + index id. E.g. crate_mine00000001"""
        return '%s%08X' % (self.id,self.index)
    
#------------------------------------------------------------------------------
class ListRecord(Record):
    """Leveled item or creature list. Does all the work of Levc and Levi classes."""
    def __init__(self,name,size,delFlag,recFlag,ins=None,unpack=False):
        """Initialize."""
        #--Record type.
        if name not in ('LEVC','LEVI'):
            raise ArgumentError(_('Type must be either LEVC or LEVI.'))
        #--Data
        self.id = None
        self.calcFromAllLevels = False
        self.calcForEachItem = False
        self.chanceNone = 0
        self.count = 0
        self.entries = []
        self.isDeleted = False
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        """Load data from stream or own data."""
        #--Read subrecords
        bytesRead = 0
        objectId = None
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader(self.name)
            #print name,size
            bytesRead += 8+size
            subData = ins.read(size, self.name+'.'+name)
            #--Id?
            if name == 'NAME':
                self.id = cstrip(subData)
            #--Flags
            elif name == 'DATA':
                flags = struct.unpack('i',subData)[0]
                if self.name == 'LEVC':
                    self.calcFromAllLevels = (flags & 1) == 1
                else:
                    self.calcForEachItem = (flags & 1) == 1
                    self.calcFromAllLevels = (flags & 2) == 2
            #--Chance None
            elif name == 'NNAM':
                self.chanceNone = struct.unpack('B',subData)[0]
            #--Count
            elif name == 'INDX':
                self.count = struct.unpack('i',subData)[0]
            #--Creature/Item Id?
            elif name == 'CNAM' or name == 'INAM':
                objectId = cstrip(subData)
            #--PC Level
            elif name == 'INTV':
                pcLevel = struct.unpack('h',subData)[0]
                self.entries.append((pcLevel,objectId))
                objectId = None
            #--Deleted?
            elif name == 'DELE': 
                self.isDeleted = True
            #--Else
            else: raise Tes3UnknownSubRecord(self.inName,name,self.name)
        #--No id?
        if not self.id:
            raise Tes3Error(self.inName,_('No id for %s record.') % (self.name,))
        #--Bad count?
        if self.count != len(self.entries):
            self.count = len(self.entries)
            self.setChanged()

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Header
        out.packSub0('NAME',self.id)
        if getattr(self,'isDeleted',False):
            out.packSub('DELE','i',0)
            return
        if self.name == 'LEVC':
            flags = 1*self.calcFromAllLevels
            etype = 'CNAM'
        else:
            flags = 1*self.calcForEachItem + 2*self.calcFromAllLevels
            etype = 'INAM'
        out.packSub('DATA','i',flags)
        out.packSub('NNAM','B',self.chanceNone)
        out.packSub('INDX','i',len(self.entries))
        #--Entries
        for pcLevel, objectId in self.entries:
            out.packSub0(etype,objectId)
            out.packSub('INTV','h',pcLevel)

    def mergeWith(self,newLevl):
        """Merges newLevl settings and entries with self."""
        #--Clear
        self.data = None
        self.setChanged()
        #--Merge settings
        self.isDeleted = newLevl.isDeleted
        self.chanceNone = newLevl.chanceNone
        self.calcFromAllLevels = self.calcFromAllLevels or newLevl.calcFromAllLevels
        self.calcForEachItem = self.calcForEachItem or newLevl.calcForEachItem
        #--Merge entries
        entries = self.entries
        oldEntries = set(entries)
        for entry in newLevl.entries:
            if entry not in oldEntries:
                entries.append(entry)
        #--Sort entries by pcLevel
        self.entries.sort(key=lambda a: a[0])

# TES3 Data --------------------------------------------------------------------
#------------------------------------------------------------------------------
class Book(Record):
    """BOOK record."""
    def __init__(self,name='BOOK',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialization."""
        self.model = 'Add Art File'
        self.teaches = -1
        self.weight = self.value = self.isScroll = self.enchantPoints = 0
        self.title = self.script = self.icon = self.text = self.enchant = None
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        """Loads from ins/internal data."""
        self.isDeleted = False
        #--Read subrecords
        bytesRead = 0
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('BOOK')
            srData = ins.read(size,'BOOK.'+name)
            bytesRead += 8+size
            if   name == 'NAME': self.id = cstrip(srData)
            elif name == 'MODL': self.model = cstrip(srData)
            elif name == 'FNAM': self.title = cstrip(srData)
            elif name == 'BKDT':
                (self.weight,self.value,self.isScroll,self.teaches,self.enchantPoints
                    ) = struct.unpack('f4i',srData)
            elif name == 'SCRI': self.script = cstrip(srData)
            elif name == 'ITEX': self.icon = cstrip(srData)
            elif name == 'TEXT': self.text = cstrip(srData)
            elif name == 'ENAM': self.enchant = cstrip(srData)
            #--Deleted?
            elif name == 'DELE': self.isDeleted = True
            #--Bad record?
            else: 
                raise Tes3Error(self.inName,_('Extraneous subrecord (%s) in %s record.') 
                    % (name,self.name))

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        out.packSub0('NAME',self.id)
        if getattr(self,'isDeleted',False):
            out.packSub('DELE','i',0)
            return
        out.packSub0('MODL',self.model)
        if self.title:   out.packSub0('FNAM',self.title)
        out.packSub('BKDT','f4i',
            self.weight, self.value, self.isScroll, self.teaches, self.enchantPoints)
        if self.script:  out.packSub0('SCRI',self.script)
        if self.icon:    out.packSub0('ITEX',self.icon)
        if self.text:    out.packSub0('TEXT',self.text)
        if self.enchant: out.packSub0('TEXT',self.enchant)

# ------------------------------------------------------------------------------
class Cell_Acdt(SubRecord):
    """In-game character attributes sub-record."""
    pass

# ------------------------------------------------------------------------------
class Cell_Chrd(SubRecord):
    """In-game character skill sub-record."""
    pass

# ------------------------------------------------------------------------------
class Cell_Frmr:
    """Proxy for FRMR/NAME record combo. Exists only to keep other functions from getting confused."""
    def __init__(self):
        self.name = 'FRMR_PROXY'

#-------------------------------------------------------------------------------
class Cell_Objects:
    """Objects in cell. Combines both early and temp objects."""
    def __init__(self,cell):
        self.cell = cell

    def list(self):
        """Return combined list of early and temp objects."""
        return self.cell.objects+self.cell.tempObjects

    def remove(self,object):
        """Remove specified object from appropriate list."""
        if object in self.cell.objects:
            self.cell.objects.remove(object)
        else:
            self.cell.tempObjects.remove(object)
        self.cell.setChanged()

    def replace(self,object,newObject):
        """Replace old object with new object."""
        if object in self.cell.objects:
            objIndex = self.cell.objects.index(object)
            self.cell.objects[objIndex] = newObject
        else:
            objIndex = self.cell.tempObjects.index(object)
            self.cell.tempObjects[objIndex] = newObject
        self.cell.setChanged()

    def isTemp(self,object):
        """Return True if object is a temp object."""
        return (object in self.tempObjects)

#-------------------------------------------------------------------------------
class Cell(Record):
    """Cell record. Name, region, objects in cell, etc."""
    def __init__(self,name='CELL',size=0,delFlag=0,recFlag=0,ins=None,unpack=False,skipObjRecords=False):
        #--Arrays
        self.skipObjRecords = skipObjRecords
        self.records = [] #--Initial records
        self.objects = []
        self.tempObjects = []
        self.endRecords = [] #--End records (map notes)
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        skipObjRecords = self.skipObjRecords
        #--Name
        (name,size) = ins.unpackSubHeader('CELL','NAME')
        self.cellName = cstrip(ins.read(size,'CELL.NAME'))
        bytesRead = 8+size
        #--Other Records
        subGroup = 0 #--0:(start) records; 10: (early) objects; 20: temp objects; 30:end records
        nam0 = 0 #--Temp record count from file
        printCell = 0
        objRecords = None
        isMoved = False
        isSpawned = False
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('CELL')
            #--New reference?
            if name == 'FRMR':
                if not subGroup: subGroup = 10
                #--Spawned? Then just another subrecord.
                if isSpawned:
                    isSpawned = False
                    if skipObjRecords:
                        ins.seek(size,1,'CELL.FRMR')
                    else:
                        objRecords.append(SubRecord(name,size,ins))
                    bytesRead += 8 + size
                #--New Record?
                else:
                    if size != 4: raise Tes3SizeError(self.inName,'CELL.FRMR',size,4,True)
                    rawData = ins.read(4,'CELL.FRMR')
                    iMod = struct.unpack('3xB',rawData)[0]
                    iObj = struct.unpack('i',rawData[:3]+'\x00')[0]
                    bytesRead  += 12
                    (name,size) = ins.unpackSubHeader('CELL','NAME')
                    objId = cstrip(ins.read(size,'CELL.NAME_NEXT'))
                    bytesRead += 8 + size
                    if skipObjRecords:
                        pass
                    elif isMoved:
                        isMoved = False
                        objRecords.append(Cell_Frmr())
                    else:
                        objRecords = [Cell_Frmr()]
                    #--Save Object
                    object = (iMod,iObj,objId,objRecords)
                    if subGroup == 10:
                        self.objects.append(object)
                    else:
                        self.tempObjects.append(object)
                    #print '  %7d %3d %s' % (iObj,iMod,objId)
            #--Leveled Creature? (Ninja Monkey)
            elif name == 'LVCR':
                isSpawned = True
                if skipObjRecords:
                    ins.seek(size,1,'CELL.LVCR')
                else:
                    objRecords.append(SubRecord(name,size,ins))
                bytesRead += 8 + size
            #--Map Note?
            elif name == 'MPCD':
                subGroup = 30
                self.endRecords.append(SubRecord(name,size,ins))
                bytesRead += 8 + size
            #--Move Ref?
            elif name == 'MVRF' and not isSpawned:
                if not subGroup: subGroup = 10
                isMoved = True
                if skipObjRecords:
                    ins.seek(size,1,'CELL.MVRF')
                else:
                    objRecords = [SubRecord(name,size,ins)]
                bytesRead += 8 + size
            #--Map Note?
            elif name == 'NAM0':
                if subGroup >= 20:
                    raise Tes3Error(self.ins, self.getId()+_(': Second NAM0 subrecord.'))
                subGroup = 20
                if size != 4: raise Tes3SizeError(self.inName,'CELL.NAM0',size,4,True)
                if size != 4: raise Tes3SizeError(self.inName,'CELL.NAM0',size,4,True)
                nam0 = ins.unpack('i',4,'CELL.NAM0')[0]
                bytesRead += 8 + size
            #--Start subrecord?
            elif not subGroup:
                record = SubRecord(name,size,ins)
                self.records.append(record)
                if name == 'DATA':
                    (self.flags,self.gridX,self.gridY) = struct.unpack('3i',record.data)
                bytesRead += 8 + size
                #print ' ',name,size
            #--Object sub-record?
            elif subGroup < 30:
                #if isSpawned:
                #    print 'Spawn subrecord',self.objects[-1][:3],name
                if skipObjRecords:
                    ins.seek(size,1,'CELL.SubRecord')
                else:
                    objRecords.append(SubRecord(name,size,ins))
                bytesRead += 8 + size
                #print '    ',name,size
            #--End subrecord?
            elif subGroup == 30:
                self.endRecords.append(SubRecord(name,size,ins))
                bytesRead += 8 + size
                #print ' ',name,size
            #print ' ',name,size
        #--Nam0 miscount?
        if nam0 != len(self.tempObjects):
            self.setChanged()

    def getObjects(self):
        """Return a Cell_Objects instance."""
        return Cell_Objects(self)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Get sizes and dump into dataIO
        out.packSub0('NAME',self.cellName)
        #--Hack: Insert data record if necessary
        for record in self.records:
            if record.name == 'DATA': break
        else:
            self.records.insert(0,SubRecord('DATA',0))
        #--Top Records
        for record in self.records:
            if record.name == 'DATA':
                record.setData(struct.pack('3i',self.flags,self.gridX,self.gridY))
            record.getSize()
            record.dump(out)
        #--Objects
        inTempObjects = False
        for object in self.getObjects().list():
            #--Begin temp objects?
            if not inTempObjects and (object in self.tempObjects):
                out.packSub('NAM0','i',len(self.tempObjects))
                inTempObjects = True
            (iMod,iObj,objId,objRecords) = object
            for record in objRecords:
                #--FRMR/NAME placeholder?
                if isinstance(record,Cell_Frmr):
                    out.pack('4si','FRMR',4)
                    out.write(struct.pack('i',iObj)[:3])
                    out.pack('B',iMod)
                    out.packSub0('NAME',objId)
                else:
                    record.getSize()
                    record.dump(out)
        #--End Records
        for endRecord in self.endRecords:
            endRecord.getSize()
            endRecord.dump(out)

    def getId(self):
        #--Interior Cell?
        if (self.flags & 1):
            return self.cellName
        else:
            return ('[%d,%d]' % (self.gridX,self.gridY))

    def cmpId(self,other):
        """Return cmp value compared to other cell for sorting."""
        selfIsInterior = self.flags & 1
        otherIsInterior = other.flags & 1
        #--Compare exterior/interior. (Exterior cells sort to top.)
        if selfIsInterior != otherIsInterior:
            #--Return -1 if self is exterior
            return (-1 + 2*(selfIsInterior))
        #--Interior cells?
        elif selfIsInterior:
            return cmp(self.cellName,other.cellName)
        #--Exterior cells?
        elif self.gridX != other.gridX:
            return cmp(self.gridX,other.gridX)
        else:
            return cmp(self.gridY,other.gridY)

#------------------------------------------------------------------------------
class Crec(ContentRecord):
    """CREC record. Creature contents."""
    def __init__(self,name='CREC',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.index = 0
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Name
        (name,size) = ins.unpackSubHeader('CREC','NAME')
        self.id = cstrip(ins.read(size,'CREC.NAME'))
        #--Index
        (name,size) = ins.unpackSubHeader('CELL','INDX')
        self.index = ins.unpack('i',size,'CREC.INDX')[0]

#------------------------------------------------------------------------------
class Cntc(ContentRecord):
    """CNTC record. Container contents."""
    def __init__(self,name='CNTC',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.index = 0
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Name
        (name,size) = ins.unpackSubHeader('CNTC','NAME')
        self.id = cstrip(ins.read(size,'CNTC.NAME'))
        #--Index
        (name,size) = ins.unpackSubHeader('CNTC','INDX')
        self.index = ins.unpack('i',size,'CTNC.INDX')[0]

#------------------------------------------------------------------------------
class Dial(Record):
    """DIAL record. Name of dialog topic/greeting/journal name, etc."""
    def __init__(self,name='DIAL',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.type = 0
        self.unknown1 = None
        self.dele = None
        self.data = None
        self.infos = []
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Id
        (name,size) = ins.unpackSubHeader('DIAL','NAME')
        self.id = cstrip(ins.read(size,'DIAL.NAME'))
        bytesRead = 8+size
        #--Type
        (name,size) = ins.unpackSubHeader('DIAL','DATA')
        if size == 1:
            self.type = ins.unpack('B',size,'DIAL.DATA')[0]
        elif size == 4:
            (self.type,self.unknown1) = ins.unpack('B3s',size,'DIAL.DATA')
        else:
            raise Tes3SizeError(self.inName,'DIAL.DATA',size,4,False)
        bytesRead += 8+size
        #--Dele?
        if size == 4:
            (name,size) = ins.unpackSubHeader('DIAL','DELE')
            self.dele = ins.read(size,'DIAL.DELE')
            bytesRead += 8+size
        if bytesRead != self.size:
            raise Tes3Error(self.inName,_('DIAL %d %s: Unexpected subrecords') % (self.type,self.id))

    def sortInfos(self):
        """Sorts infos by link order."""
        #--Build infosById
        infosById = {}
        for info in self.infos:
            if info.id == None: raise Tes3Error(self.inName,_('Dialog %s: info with missing id.') % (self.id,))
            infosById[info.id] = info
        #--Heads
        heads = []
        for info in self.infos:
            if info.prevId not in infosById:
                heads.append(info)
        #--Heads plus their next chains
        newInfos = []
        for head in heads:
            nextInfo = head
            while nextInfo:
                newInfos.append(nextInfo)
                nextInfo = infosById.get(nextInfo.nextId)
        #--Anything left?
        for info in self.infos:
            if info not in newInfos:
                newInfos.append(info)
        #--Replace existing list
        self.infos = newInfos

#------------------------------------------------------------------------------
class Fmap(Record):
    """FMAP record. Worldmap for savegame."""
    #--Class data
    DEEP    = rgbString(25,36,33)
    SHALLOW = rgbString(37,55,50)
    LAND    = rgbString(62,45,31)
    GRID    = rgbString(27,40,37)
    BORDER  = SHALLOW
    MARKED  = rgbString(202,165,96)

    def __init__(self,name='FMAP',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialize."""
        self.mapd = None #--Array of 3 byte strings when expanded (512x512)
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Header
        out.packSub('MAPH','ii',512,9)
        #--Data
        out.pack('4si','MAPD',512*512*3)
        out.write(''.join(self.mapd))

    def edit(self):
        """Prepare data for editing."""
        wmap = 512
        if not self.mapd:
            data = self.data[24:]
            mapd = self.mapd = []
            for index in xrange(0,3*wmap*wmap,3):
                mapd.append(data[index:index+3])
        self.setChanged()

    def drawRect(self,color,x1,y1,x2,y2):
        """Draw rectangle of specified color."""
        if not self.changed: self.edit()
        wmap = 512
        mapd = self.mapd
        for y in xrange(y1,y2):
            ymoff = wmap*y
            for x in xrange(x1,x2):
                mapd[x+ymoff] = color

    def drawBorder(self,color,x1,y1,x2,y2,thick):
        """Draw's a border rectangle of specified thickness."""
        self.drawRect(color,x1,y1,x2,y1+thick)
        self.drawRect(color,x1,y1,x1+thick,y2)
        self.drawRect(color,x2-thick,y1,x2,y2)
        self.drawRect(color,x1,y2-thick,x2,y2)

    def drawGrid(self,gridLines=True):
        """Draw grid for visible map."""
        if not self.changed: self.edit()
        cGrid = Fmap.GRID
        cBorder = Fmap.BORDER
        if gridLines: #--Some fools don't want the grid!
            #--Grid
            for uv in range(-25,26,5):
                xy = 512/2 - 9*uv + 4
                self.drawRect(cGrid,0,xy,512,xy+1)
                self.drawRect(cGrid,xy,0,xy+1,512)
            #--Grid axes
            xy = 512/2 + 4
            self.drawRect(cBorder,0,xy,512,xy+1)
            self.drawRect(cBorder,xy,0,xy+1,512)
        #--Border
        self.drawBorder(cBorder,0,0,512,512,4)

    def drawCell(self,land,uland,vland,marked):
        """Draw a cell from landscape record."""
        from math import sqrt, pow
        #--Tranlate grid point (u,v) to pixel point
        if not self.changed: self.edit()
        #--u/v max/min are grid range of visible map. 
        #--wcell is bit width of cell. 512 is bit width of visible map.
        (umin,umax,vmin,vmax,wcell,wmap) = (-28,27,-27,28,9,512)
        if not ((umin <= uland <= umax) and (vmin <= vland <= vmax)):
            return
        #--x0,y0 is bitmap coordinates of top left of cell in visible map.
        (x0,y0) = (4 + wcell*(uland-umin), 4 + wcell*(vmax-vland))
        #--Default to deep
        mapc = [Fmap.DEEP]*(9*9)
        heights = land and land.getHeights()
        if heights:
            #--Land heights are in 65*65 array, starting from bottom left. 
            #--Coordinate conversion. Subtract one extra from height array because it's edge to edge.
            converter = [(65-2)*px/(wcell-1) for px in range(wcell)]
            for yc in range(wcell):
                ycoff = wcell*yc
                yhoff = (65-1-converter[yc])*65
                for xc in range(wcell):
                    height = heights[converter[xc]+yhoff]
                    if height >= 0: #--Land
                        (r0,g0,b0,r1,g1,b1,scale) = (66,48,33,32,23,16,sqrt(height/3000.0))
                        scale = int(scale*10)/10.0 #--Make boundaries sharper.
                        r = chr(max(0,int(r0 - r1*scale)) & ~1)
                    else: #--Sea
                        #--Scale color from shallow to deep color.
                        (r0,g0,b0,r1,g1,b1,scale) = (37,55,50,12,19,17,-height/2048.0)
                        r = chr(max(0,int(r0 - r1*scale)) | 1)
                    g = chr(max(0,int(g0 - g1*scale)))
                    b = chr(max(0,int(b0 - b1*scale)))
                    mapc[xc+ycoff] = r+g+b
        #--Draw it
        mapd = self.mapd
        for yc in range(wcell):
            ycoff = wcell*yc
            ymoff = wmap*(y0+yc)
            for xc in range(wcell):
                cOld = mapd[x0+xc+ymoff]
                cNew = mapc[xc+ycoff]
                rOld = ord(cOld[0])
                #--New or old is sea.
                if (ord(cNew[0]) & 1) or ((rOld & 1) and
                    (-2 < (1.467742*rOld - ord(cOld[1])) < 2) and
                    (-2 < (1.338710*rOld - ord(cOld[2])) < 2)):
                    mapd[x0+xc+ymoff] = cNew
        if marked:
            self.drawBorder(Fmap.MARKED,x0+2,y0+2,x0+7,y0+7,1)
            pass

#------------------------------------------------------------------------------
class Glob(Record):
    """Global record. Note that global values are stored as floats regardless of type."""
    def __init__(self,name='GLOB',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialization."""
        self.type = 'l'
        self.value = 0
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        """Loads from ins/internal data."""
        #--Read subrecords
        bytesRead = 0
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('GLOB')
            srData = ins.read(size,'GLOB.'+name)
            bytesRead += 8+size
            if   name == 'NAME': self.id = cstrip(srData)
            elif name == 'FNAM': self.type = srData
            elif name == 'FLTV': self.value = struct.unpack('f',srData)
            #--Deleted?
            elif name == 'DELE': self.isDeleted = True
            #--Bad record?
            else: raise Tes3UnknownSubRecord(self.inName,name,self.name)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        out.packSub0('NAME',self.id)
        if getattr(self,'isDeleted',False):
            out.packSub('DELE','i',0)
            return
        out.packSub('FNAM',self.type)
        out.packSub('FLTV','f',self.value)

#------------------------------------------------------------------------------
class Info_Test:
    """INFO function/variable test. Equates to SCVR + INTV/FLTV."""
    def __init__(self,type,func,oper,text='',value=0):
        """Initialization."""
        self.type = type
        self.func = func
        self.oper = oper
        self.text = text
        self.value = value

    def dumpData(self,out,index):
        """Dumps self into specified out stream with specified SCVR index value."""
        #--SCVR
        out.pack('4siBB2sB',
            'SCVR', 5+len(self.text), index+48, self.type, self.func, self.oper)
        if self.text: out.write(self.text)
        #--Value
        if isinstance(self.value,int):
            out.packSub('INTV','i', self.value)
        else:
            out.packSub('FLTV','f', self.value)

#------------------------------------------------------------------------------
class Info(Record):
    """INFO record. Dialog/journal entry. This version is complete."""
    def __init__(self,name='INFO',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialization."""
        #--Info Id
        self.id = ''
        self.nextId = ''
        self.prevId = ''
        #--Text/Script
        self.text = None
        self.script = None
        self.speak = None
        self.qflag = 0 # 0 nothing, 1 name, 2 finished, 3 restart.
        #--Unknown
        self.type = 0 #--Same as for dial.
        self.unk02 = 0
        #--Speaker Tests
        self.spDisp = 0
        self.spSex = -1
        self.spRank = -1
        self.spId = None
        self.spRace = None
        self.spClass = None
        self.spFaction = None
        #--Cell, PC
        self.cell = None
        self.pcRank = -1
        self.pcFaction = None
        #--Other Tests
        self.tests = [0,0,0,0,0,0]
        #--Deleted?
        self.isDeleted = False
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        """Loads from ins/internal data."""
        #--Read subrecords
        bytesRead = 0
        curTest = None
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('INFO')
            srData = ins.read(size,'INFO.'+name)
            bytesRead += 8+size
            #--Ids
            if   name == 'INAM': self.id = cstrip(srData)
            elif name == 'PNAM': self.prevId = cstrip(srData)
            elif name == 'NNAM': self.nextId = cstrip(srData)
            #--Text/Script
            elif name == 'NAME': self.text = srData
            elif name == 'BNAM': self.script = srData
            elif name == 'SNAM': self.speak = srData
            #--Quest flags
            elif name == 'QSTN': self.qflag = 1
            elif name == 'QSTF': self.qflag = 2
            elif name == 'QSTR': self.qflag = 3
            #--String/Value Tests
            elif name == 'DATA': 
                (self.type, self.spDisp, self.spRank, self.spSex, self.pcRank, self.unk02
                    ) = struct.unpack('2i4B',srData)
            elif name == 'ONAM': self.spId = cstrip(srData)
            elif name == 'RNAM': self.spRace = cstrip(srData)
            elif name == 'CNAM': self.spClass = cstrip(srData)
            elif name == 'FNAM': self.spFaction = cstrip(srData)
            elif name == 'ANAM': self.cell = cstrip(srData)
            elif name == 'DNAM': self.pcFaction = cstrip(srData)
            #--Function/Value Tests
            elif name == 'SCVR': 
                (index,type,func,oper) = struct.unpack('BB2sB',srData[:5])
                text = srData[5:]
                curTest = Info_Test(type,func,oper,text)
                self.tests[index-48] = curTest
            elif name == 'INTV':
                (curTest.value,) = struct.unpack('i',srData)
            elif name == 'FLTV':
                (curTest.value,) = struct.unpack('f',srData)
            #--Deleted?
            elif name == 'DELE': self.isDeleted = True
            #--Bad record?
            else: raise Tes3UnknownSubRecord(self.inName,name,self.name)

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        out.packSub0('INAM',self.id)
        out.packSub0('PNAM',self.prevId)
        out.packSub0('NNAM',self.nextId)
        if not self.isDeleted:
            out.packSub('DATA','2i4B',
                self.type, self.spDisp, self.spRank, self.spSex, self.pcRank, self.unk02)
        if self.spId:       out.packSub0('ONAM',self.spId)
        if self.spRace:     out.packSub0('RNAM',self.spRace)
        if self.spClass:    out.packSub0('CNAM',self.spClass)
        if self.spFaction:  out.packSub0('FNAM',self.spFaction)
        if self.cell:       out.packSub0('ANAM',self.cell)
        if self.pcFaction:  out.packSub0('DNAM',self.pcFaction)
        if self.speak:      out.packSub0('SNAM',self.speak)
        if self.text:       out.packSub('NAME',self.text)
        if self.qflag == 0:
            pass
        if self.qflag == 1: out.packSub('QSTN','\x01')
        if self.qflag == 2: out.packSub('QSTF','\x01')
        if self.qflag == 3: out.packSub('QSTR','\x01')
        for index,test in enumerate(self.tests):
            if test: test.dumpData(out,index)
        if self.script:     out.packSub('BNAM',self.script)
        if self.isDeleted:  out.pack('DELE','i',0)

    def compactTests(self,mode='TOP'):
        """Compacts test array. I.e., moves test up into any empty slots if present.
        mode: 'TOP' Eliminate only leading empty tests. [0,0,1,0,1] >> [1,0,1]
        mode: 'ALL' Eliminat all empty tests. [0,0,1,0,1] >> [1,1]"""
        if tuple(self.tests) == (0,0,0,0,0,0): return False
        if mode == 'TOP':
            newTests = self.tests[:]
            while newTests and not newTests[0]:
                del newTests[0]
        else:
            newTests = [test for test in self.tests if test]
        while len(newTests) < 6: newTests.append(0)
        if tuple(self.tests) != tuple(newTests):
            self.tests = newTests
            self.setChanged()
            return True

#------------------------------------------------------------------------------
class InfoS(Record):
    """INFO record. Dialog/journal entry.
    This is a simpler version of the info record. It expands just enough for 
    dialog import/export."""
    def __init__(self,name='INFO',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.nextId = None
        self.prevId = None
        self.spId = None
        self.text = None
        self.records = [] #--Subrecords, of course
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Read subrecords
        bytesRead = 0
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('INFO')
            #print name,size
            bytesRead += 8+size
            record = SubRecord(name,size,ins)
            self.records.append(record)
            #--Info Id?
            if name == 'INAM':
                self.id = cstrip(record.data)
            elif name == 'PNAM':
                self.prevId = cstrip(record.data)
            elif name == 'NNAM':
                self.nextId = cstrip(record.data)
            #--Speaker?
            elif name == 'ONAM':
                self.spId = cstrip(record.data)
            #--Text?
            elif name == 'NAME':
                self.text = record.data

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Get sizes
        for record in self.records:
            #--Text
            if record.name == 'NAME':
                #--Truncate text?
                if len(self.text) > 511:
                    self.text = self.text[:511]
                record.data = self.text
                record.size = len(self.text)
            #--Speaker
            elif record.name == 'ONAM':
                record.data = self.spId+'\x00'
                record.size = len(self.spId) + 1
            record.getSize()
            record.dump(out)

#------------------------------------------------------------------------------
class Land(Record):
    """LAND record. Landscape: heights, vertices, texture references, etc."""
    def __init__(self,name='LAND',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialize."""
        self.id = None
        #self.gridX = 0
        #self.gridY = 0
        self.heights = None
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def getId(self):
        """Return id. Also, extract gridX and gridY."""
        if self.id: return self.id
        reader = self.getReader()
        subData = reader.findSubRecord('INTV','LAND')
        (self.gridX,self.gridY) = struct.unpack('ii',subData)
        self.id = '[%d,%d]' % (self.gridX,self.gridY)
        return self.id

    def getHeights(self):
        """Returns len(65x65) array of vertex heights."""
        if self.heights: return self.heights
        reader = self.getReader()
        subData = reader.findSubRecord('VHGT','LAND')
        if not subData: return None
        height0 = struct.unpack('f',subData[:4])[0]
        import array
        deltas = array.array('b',subData[4:4+65*65])
        iheights = array.array('i')
        iheights.append(0)
        for index in xrange(1,65*65):
            if index % 65:
                iheights.append(iheights[-1] + deltas[index])
            else:
                iheights.append(iheights[-65] + deltas[index])
        heights = self.heights = array.array('f')
        for index in xrange(65*65):
            heights.append(8*(height0 + iheights[index]))
        return self.heights

#------------------------------------------------------------------------------
class Levc(ListRecord):
    """LEVC record. Leveled list for creatures."""
    pass

#------------------------------------------------------------------------------
class Levi(ListRecord):
    """LEVI record. Leveled list for items."""
    pass

#------------------------------------------------------------------------------
class Npcc(ContentRecord):
    """NPCC record. NPC contents/change."""
    def __init__(self,name='NPCC',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.index = 0
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Name
        (name,size) = ins.unpackSubHeader('NPCC','NAME')
        self.id = cstrip(ins.read(size,'CELL.NAME'))
        #--Index
        (name,size) = ins.unpackSubHeader('NPCC','NPDT',8)
        (unknown,self.index) = ins.unpack('ii',size,'CELL.NPDT')

#------------------------------------------------------------------------------
class Scpt(Record):
    """SCPT record. Script."""
    #--Class Data
    subRecordNames = ['SCVR','SCDT','SCTX','SLCS','SLSD','SLFD','SLLD','RNAM']

    def __init__(self,name='SCPT',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        #--Arrays
        self.id = None
        self.numShorts = 0
        self.numLongs = 0
        self.numFloats = 0
        self.dataSize = 0
        self.varSize = 0
        #--Mod data
        self.scvr = None
        self.scdt = None
        self.sctx = None
        #--Save data
        self.slcs = None
        self.slsd = None
        self.slfd = None
        self.slld = None
        self.rnam = None
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        #--Subrecords
        bytesRead = 0
        srNameSet = set(Scpt.subRecordNames)
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('SCPT')
            #--Header
            if name == 'SCHD':
                (self.id, self.numShorts, self.numLongs, self.numFloats, self.dataSize, self.varSize
                    ) = ins.unpack('32s5i',size,'SCPT.SCHD')
                self.id = cstrip(self.id)
            #--Other subrecords
            elif name in srNameSet:
                setattr(self,name.lower(),SubRecord(name,size,ins))
            else:
                raise Tes3Error(self.inName,_('Unknown SCPT record: ')+name)
            bytesRead += 8+size
        if bytesRead != self.size:
            raise Tes3Error(self.inName,_('SCPT %d %s: Unexpected subrecords') % (self.type,self.id))

    def getRef(self):
        """Returns reference data for a global script."""
        rnam = self.rnam
        if not rnam or rnam.data == chr(255)*4: return None
        if rnam.size != 4: raise Tes3Error(self.inName,_('SCPT.RNAM'),rnam.size,4,True)
        iMod = struct.unpack('3xB',rnam.data)[0]
        iObj = struct.unpack('i',rnam.data[:3]+'\x00')[0]
        return (iMod,iObj)
    
    def setRef(self,reference):
        """Set reference data for a global script."""
        (iMod,iObj) = reference
        self.rnam.setData(struct.pack('i',iObj)[:3] + struct.pack('B',iMod))
        self.setChanged()

    def setCode(self,code):
        #--SCHD
        #self.numShorts = 0
        #self.numLongs = 0
        #self.numFloats = 0
        self.dataSize = 2
        #self.varSize = 0
        #--SCDT
        if not self.scdt: self.scdt = SubRecord('SCDT',0)
        self.scdt.setData(struct.pack('BB',1,1)) #--Uncompiled
        #--SCVR
        #self.scvr = None
        #--SCTX (Code)
        if not self.sctx: self.sctx = SubRecord('SCTX',0)
        self.sctx.setData(winNewLines(code))
        #--Done
        self.setChanged()
        self.getSize()

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Header
        out.packSub('SCHD','32s5i',
            self.id, 
            self.numShorts, self.numLongs, self.numFloats, 
            self.dataSize, self.varSize)
        #--Others
        for record in [getattr(self,srName.lower(),None) for srName in Scpt.subRecordNames]:
            if not record: continue
            record.size = len(record.data)
            record.dump(out)

#------------------------------------------------------------------------------
class Tes3_Hedr(SubRecord): 
    """TES3 HEDR subrecord. File header."""
    def __init__(self,name,size,ins=None,unpack=False):
        """Initialize."""
        self.version = 1.3
        self.fileType = 0 #--0: esp; 1: esm; 32: ess
        self.author = ''
        self.description = ''
        self.numRecords = 0
        SubRecord.__init__(self,name,size,ins,unpack)

    def load(self,ins,unpack=False):
        self.data = ins.read(self.size,'TES3.HEDR')
        if not unpack: return
        data = struct.unpack('fi32s256si',self.data)
        self.version = data[0]
        self.fileType = data[1]
        self.author = cstrip(data[2])
        self.description = cstrip(data[3])
        self.numRecords = data[4]

    def getSize(self):
        if not self.data and not self.changed: raise StateError(_('Data undefined: ')+self.name)
        if not self.changed: return self.size
        self.description = winNewLines(self.description)
        self.data = struct.pack('fi32s256si',
            self.version,
            self.fileType,
            self.author,
            self.description,
            self.numRecords)
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

#------------------------------------------------------------------------------
class Tes3_Gmdt(SubRecord):
    """TES3 GMDT subrecord. Savegame data. PC name, health, cell, etc."""
    def load(self,ins,unpack=False):
        self.data = ins.read(self.size,'TES3.GMDT')
        if not unpack: return
        data = struct.unpack('3f12s64s4s32s',self.data)
        self.curHealth = data[0]
        self.maxHealth = data[1]
        self.day = data[2]
        self.unknown1 = data[3]
        self.curCell = cstrip(data[4])
        self.unknown2 = data[5]
        self.playerName = cstrip(data[6])

    def getSize(self):
        if not self.data: raise StateError(_('Data undefined: ')+self.name)
        if not self.changed: return self.size
        self.data = struct.pack('3f12s64s4s32s',
            self.curHealth,
            self.maxHealth,
            self.day,
            self.unknown1,
            self.curCell,
            self.unknown2,
            self.playerName,
            )
        self.size = len(self.data)
        self.setChanged(False)
        return self.size

#------------------------------------------------------------------------------
class Tes3(Record):
    """TES3 Record. File header."""
    def __init__(self,name='TES3',size=0,delFlag=0,recFlag=0,ins=None,unpack=False):
        """Initialize."""
        self.hedr = None
        self.masters = [] #--(fileName,fileSize)
        self.gmdt = None
        self.others = [] #--SCRD, SCRS (Screen snapshot?)
        Record.__init__(self,name,size,delFlag,recFlag,ins,unpack)

    def loadData(self,ins):
        MAX_SUB_SIZE = 100*1024
        #--Header
        (name,size) = ins.unpackSubHeader('TES3','HEDR')
        self.hedr = Tes3_Hedr(name,size,ins,True)
        bytesRead = 8+size
        #--Read Records
        while bytesRead < self.size:
            (name,size) = ins.unpackSubHeader('TES3')
            if size > MAX_SUB_SIZE: raise Tes3SizeError(self.inName,name,size,-MAX_SUB_SIZE,True)
            #--Masters
            if name == 'MAST':
                #--FileName
                fileName = cstrip(ins.read(size,'TES3.MAST'))
                bytesRead += 8 + size
                #--FileSize
                (name,size) = ins.unpackSubHeader('TES3','DATA',8)
                fileSize = ins.unpack('Q',8,'TES3.DATA')[0]
                self.masters.append((fileName,fileSize))
                bytesRead += 16
            #--Game Data
            elif name == 'GMDT':
                self.gmdt = Tes3_Gmdt(name,size,ins,True)
                bytesRead += 8 + size
            #--Screen snapshot?
            else:
                self.others.append(SubRecord(name,size,ins))
                bytesRead += 8 + size

    def dumpData(self,out):
        """Dumps state into out. Called by getSize()."""
        #--Get sizes and dump into dataIO
        self.hedr.getSize()
        self.hedr.dump(out)
        for (name,size) in self.masters:
            out.packSub0('MAST',name)
            out.packSub('DATA','Q',size)
        if self.gmdt: 
            self.gmdt.getSize()
            self.gmdt.dump(out)
        for other in self.others:
            other.getSize()
            other.dump(out)

# File System -----------------------------------------------------------------
#------------------------------------------------------------------------------
class MWIniFile:
    """Morrowind.ini file."""
    def __init__(self,dir):
        """Initialize."""
        self.dir = dir
        self.path = os.path.join(self.dir,'Morrowind.ini')
        self.preLoadLines = [] #--Temp Holder
        self.postLoadLines = [] #--Temp Holder
        self.loadFilesComment = None
        self.loadFiles = []
        self.loadFilesBad = [] #--In Morrowind.ini, but don't exist!
        self.loadFilesExtra = []
        self.mtime = 0
        self.size = 0
        self.doubleTime = {}
        self.exOverLoaded = set()
        self.loadOrder = tuple() #--Empty tuple
        
    def getSetting(self,section,key,default=None):
        """Gets a single setting from the file."""
        section,key = map(bolt.LString,(section,key))
        settings = self.getSettings()
        if section in settings:
            return settings[section].get(key,default)
        else:
            return default

    def getSettings(self):
        """Gets settings for self."""
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=(.*)')
        #--Read ini file
        #self.ensureExists()
        iniFile = GPath(self.path).open('r')
        settings = {} #settings[section][key] = value (stripped!)
        sectionSettings = None 
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                sectionSettings = settings[LString(maSection.group(1))] = {}
            elif maSetting:
                if sectionSettings == None:
                    sectionSettings = settings.setdefault(LString('General'),{})
                    self.isCorrupted = True
                sectionSettings[LString(maSetting.group(1))] = maSetting.group(2).strip()
        iniFile.close()
        return settings

    def saveSetting(self,section,key,value):
        """Changes a single setting in the file."""
        settings = {section:{key:value}}
        self.saveSettings(settings)

    def saveSettings(self,settings):
        """Applies dictionary of settings to ini file. 
        Values in settings dictionary can be either actual values or 
        full key=value line ending in newline char."""
        settings = dict((LString(x),dict((LString(u),v) for u,v in y.iteritems())) 
            for x,y in settings.iteritems())
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=')
        #--Read init, write temp
        #self.ensureExists()
        path = GPath(self.path)
        iniFile = path.open('r')
        tmpFile = path.temp.open('w')
        section = sectionSettings = None
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                section = LString(maSection.group(1))
                sectionSettings = settings.get(section,{})
            elif maSetting and LString(maSetting.group(1)) in sectionSettings:
                key = LString(maSetting.group(1))
                value = sectionSettings[key] 
                if isinstance(value,str) and value[-1] == '\n':
                    line = value
                else:
                    line = '%s=%s\n' % (key,value)
            tmpFile.write(line)
        tmpFile.close()
        iniFile.close()
        #--Done
        path.untemp()

    def applyMit(self,mitPath):
        """Read MIT file and apply its settings to morrowind.ini.
        Note: Will ONLY apply settings that already exist."""
        reComment = re.compile(';.*')
        reSection = re.compile(r'^\[\s*(.+?)\s*\]$')
        reSetting = re.compile(r'(.+?)\s*=')
        #--Read MIT file
        mitFile = open(mitPath,'r')
        sectionSettings = None
        settings = {}
        for line in mitFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                sectionSettings = settings[maSection.group(1)] = {}
            elif maSetting:
                sectionSettings[maSetting.group(1).lower()] = line
        mitFile.close()
        #--Discard Games Files (Loaded mods list) from settings
        for section in settings.keys():
            if section.lower() in ('game files','archives','mit'): 
                del settings[section]
        #--Apply it
        iniFile = open(self.path,'r')
        tmpPath = self.path+'.tmp'
        tmpFile = open(tmpPath,'w')
        section = None
        sectionSettings = {}
        for line in iniFile:
            stripped = reComment.sub('',line).strip()
            maSection = reSection.match(stripped)
            maSetting = reSetting.match(stripped)
            if maSection:
                section = maSection.group(1)
                sectionSettings = settings.get(section,{})
            elif maSetting and maSetting.group(1).lower() in sectionSettings:
                line = sectionSettings[maSetting.group(1).lower()]
            tmpFile.write(line)
        tmpFile.close()
        iniFile.close()
        #--Done
        renameFile(tmpPath,self.path,True)
        self.mtime = getmtime(self.path)

    def loadIni(self):
        """Read data from morrowind.ini file."""
        reLoadFiles = re.compile(r'^\[Game Files\](.*)')
        reLoadFile = re.compile(r'GameFile[0-9]+=(.*)$')
        #--Read file
        self.mtime = getmtime(self.path)
        self.size = os.path.getsize(self.path)
        ins = file(self.path,'rt')
        #--Pre-Load Lines
        del self.preLoadLines[:]
        del self.postLoadLines[:]
        while True:
            line = ins.readline()
            if not line: 
                ins.close()
                raise Tes3Error('Morrowind.ini', _('Morrowind.ini: [GameFiles] section not found.'))
            maLoadFiles = reLoadFiles.match(line)
            if maLoadFiles: break
            self.preLoadLines.append(line)
        #--Load Files 
        self.loadFilesComment = maLoadFiles.group(1)
        del self.loadFiles[:]
        del self.loadFilesBad[:]
        while True:
            line = ins.readline()
            maLoadFile = reLoadFile.match(line)
            if not maLoadFile: 
                if line: self.postLoadLines.append(line)
                break
            loadFile = unicode(maLoadFile.group(1), 'latin-1')
            loadPath = os.path.join(self.dir,'Data Files',loadFile)
            loadExt = os.path.splitext(loadPath)[-1].lower()
            if len(self.loadFiles) == 255:
                self.loadFilesExtra.append(loadFile)
            elif os.path.exists(loadPath) and re.match('^\.es[pm]$',loadExt):
                self.loadFiles.append(loadFile)
            else:
                self.loadFilesBad.append(loadFile)
        #--Post-Load Lines
        while True:
            line = ins.readline()
            if not line: break
            self.postLoadLines.append(line)
        #--Done
        ins.close()

    def save(self):
        """Write data to morrowind.ini file."""
        if self.hasChanged(): raise StateError(_('Morrowind.ini has changed'))
        out = file(self.path,'wt')
        for line in self.preLoadLines:
            out.write(line)
        out.write("[Game Files]"+self.loadFilesComment+"\n")
        for loadDex in range(len(self.loadFiles)):
            loadFile = self.loadFiles[loadDex]
            out.write('GameFile%d=%s\n' % (loadDex,loadFile.encode('latin-1')))
        for line in self.postLoadLines:
            out.write(line)
        out.close()
        self.mtime = getmtime(self.path)
        self.size = os.path.getsize(self.path)
        del self.loadFilesBad[:] #--Disappear on write.
        del self.loadFilesExtra[:] #--Disappear on write.

    def makeBackup(self):
        """Create backup copy/copies of morrowind.ini file."""
        #--File Path
        original = self.path
        #--Backup
        backup = self.path+'.bak'
        shutil.copy(original,backup)
        #--First backup
        firstBackup = self.path+'.baf'
        if not os.path.exists(firstBackup):
            shutil.copy(original,firstBackup)
    
    def safeSave(self):
        """Safe save."""
        self.makeBackup()
        self.save()

    def hasChanged(self):
        """True if morrowind.ini file has changed."""
        return ((self.mtime != getmtime(self.path)) or
            (self.size != os.path.getsize(self.path)) )

    def refresh(self):
        """Load only if morrowind.ini has changed."""
        hasChanged = self.hasChanged()
        if hasChanged: self.loadIni()
        if len(self.loadFiles) > 255:
            del self.loadFiles[255:]
            self.safeSave()
        return hasChanged

    def refreshDoubleTime(self):
        """Refresh arrays that keep track of doubletime mods."""
        doubleTime = self.doubleTime
        doubleTime.clear()
        for loadFile in self.loadFiles:
            mtime = modInfos[loadFile].mtime
            doubleTime[mtime] = doubleTime.has_key(mtime)
        #--Refresh overLoaded too..
        exGroups = set()
        self.exOverLoaded.clear()
        for selFile in self.loadFiles:
            maExGroup = reExGroup.match(selFile)
            if maExGroup: 
                exGroup = maExGroup.group(1)
                if exGroup not in exGroups:
                    exGroups.add(exGroup)
                else:
                    self.exOverLoaded.add(exGroup)

    def isWellOrdered(self,loadFile=None):
        if loadFile and loadFile not in self.loadFiles:
            return True
        elif loadFile:
            #An attempt at a fix for issue #27
            #I am not sure why this is now needed and wasn't before.
            #One posibility is that when modInfos gets manipulated this isn't
            #refreshed.
            mtime = modInfos[loadFile].mtime
            if mtime not in self.doubleTime:
                self.refreshDoubleTime()
            return not self.doubleTime[mtime]
        else:
            return not (True in self.doubleTime.values())

    def getDoubleTimeFiles(self):
        dtLoadFiles = []
        for loadFile in self.loadFiles:
            if self.doubleTime[modInfos[loadFile].mtime]:
                dtLoadFiles.append(loadFile)
        return dtLoadFiles

    def sortLoadFiles(self):
        """Sort load files into esm/esp, alphabetical order."""
        self.loadFiles.sort()
        self.loadFiles.sort(lambda a,b: cmp(a[-3:].lower(), b[-3:].lower()))
    
    #--Loading
    def isMaxLoaded(self):
        """True if load list is full."""
        return len(self.loadFiles) >= 255

    def isLoaded(self,modFile):
        """True if modFile is in load list."""
        return (modFile in self.loadFiles)

    def load(self,modFile,doSave=True):
        """Add modFile to load list."""
        if modFile not in self.loadFiles:
            if self.isMaxLoaded():
                raise MaxLoadedError
            self.loadFiles.append(modFile)
            if doSave:
                self.sortLoadFiles()
                self.safeSave()
        self.refreshDoubleTime()
        self.loadOrder = modInfos.getLoadOrder(self.loadFiles)

    def unload(self,modFile,doSave=True):
        """Remove modFile from load list."""
        while modFile in self.loadFiles:
            self.loadFiles.remove(modFile)
            if doSave: self.safeSave()
        self.refreshDoubleTime()
        self.loadOrder = modInfos.getLoadOrder(self.loadFiles)

#------------------------------------------------------------------------------
class MasterInfo:
    def __init__(self,name,size):
        self.oldName = self.name = name
        self.oldSize = self.size = size
        self.modInfo = modInfos.get(self.name,None)
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.author = self.modInfo.tes3.hedr.author
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.author = ''
            self.masterNames = tuple()
        self.isLoaded = True
        self.isNew = False #--Master has been added
    
    def setName(self,name):
        self.name = name
        self.modInfo = modInfos.get(self.name,None)
        if self.modInfo:
            self.mtime = self.modInfo.mtime
            self.size = self.modInfo.size
            self.author = self.modInfo.tes3.hedr.author
            self.masterNames = self.modInfo.masterNames
        else:
            self.mtime = 0
            self.size = 0
            self.author = ''
            self.masterNames = tuple()

    def hasChanged(self):
        return (
            (self.name != self.oldName) or
            (self.size != self.oldSize) or
            (not self.isLoaded) or self.isNew)

    def isWellOrdered(self):
        if self.modInfo:
            return self.modInfo.isWellOrdered()
        else:
            return 1

    def getStatus(self):
        if not self.modInfo: 
            return 30
        elif self.size != self.modInfo.size:
            return 10
        else:
            return 0
    
    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name)
        if not (mwIniFile.isLoaded(self.name) and maExGroup):
            return False
        else:
            return (maExGroup.group(1) in mwIniFile.exOverLoaded)

    #--Object maps
    def getObjectMap(self):
        if self.name == self.oldName:
            return None
        else:
            return modInfos.getObjectMap(self.oldName,self.name)

#------------------------------------------------------------------------------
class FileInfo:
    """Abstract TES3 File."""
    def __init__(self,dir,name):
        self.dir = dir
        self.name = name
        path = os.path.join(dir,name)
        if os.path.exists(path):
            self.ctime = os.path.getctime(path)
            self.mtime = getmtime(path)
            self.size = os.path.getsize(path)
        else:
            self.ctime = time.time()
            self.mtime = time.time()
            self.size = 0
        self.tes3 = 0
        self.masterNames = tuple()
        self.masterOrder = tuple()
        self.masterSizes = {}
        self.madeBackup = False
        #--Ancillary storage
        self.extras = {}

    #--File type tests
    def isMod(self):
        return self.isEsp() or self.isEsm()
    def isEsp(self):
        return self.name[-3:].lower() == 'esp'
    def isEsm(self):
        return self.name[-3:].lower() == 'esm'
    def isEss(self):
        return self.name[-3:].lower() == 'ess'

    def sameAs(self,fileInfo):
        return (
            (self.size == fileInfo.size) and
            (self.mtime == fileInfo.mtime) and
            (self.ctime == fileInfo.ctime) and
            (self.name == fileInfo.name) )

    def refresh(self):
        path = os.path.join(self.dir,self.name)
        self.ctime = os.path.getctime(path)
        self.mtime = getmtime(path)
        self.size = os.path.getsize(path)
        if self.tes3: self.getHeader()

    def setType(self,type):
        self.getHeader()
        if type == 'esm':
            self.tes3.hedr.fileType = 1
        elif type == 'esp':
            self.tes3.hedr.fileType = 0
        elif type == 'ess':
            self.tes3.hedr.fileType = 32
        self.tes3.hedr.setChanged()
        self.writeHedr()

    def getHeader(self):
        path = os.path.join(self.dir,self.name)
        try:
            ins = Tes3Reader(self.name,file(path,'rb'))
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            if name != 'TES3': raise Tes3Error(self.name,_('Expected TES3, but got ')+name)
            self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        except struct.error, rex:
            ins.close()
            raise Tes3Error(self.name,'Struct.error: '+`rex`)
        except Tes3Error, error:
            ins.close()
            error.inName = self.name
            raise
        ins.close()
        #--Master sizes (for getMasterStatus)
        masterNames = []
        self.masterSizes.clear()
        for (master,size) in self.tes3.masters:
            self.masterSizes[master] = size
            masterNames.append(master)
        self.masterNames = tuple(masterNames)
        self.masterOrder = tuple() #--Reset to empty for now
        #--Free some memory
        self.tes3.data = None
        self.tes3.others = None
        #--Done
        ins.close()

    def getMasterStatus(self,masterName):
        #--Exists?
        if not modInfos.has_key(masterName):
            return 30
        #--Sizes differ?
        elif ((masterName in self.masterSizes) and 
            (self.masterSizes[masterName] != modInfos[masterName].size)):
            return 10
        #--Okay?
        else:
            return 0
    
    def getStatus(self):
        status = 0
        #--Worst status from masters
        for masterName in self.masterSizes.keys():
            status = max(status,self.getMasterStatus(masterName))
        #--Missing files?
        if status == 30: 
            return status
        #--Natural misordering?
        self.masterOrder = modInfos.getLoadOrder(self.masterNames)
        if self.masterOrder != self.masterNames:
            return 20
        else:
            return status

    #--New File
    def writeNew(self,masters=[],mtime=0):
        """Creates a new file with the given name, masters and mtime."""
        tes3 = Tes3()
        tes3.hedr = Tes3_Hedr('HEDR',0)
        if   self.isEsp(): tes3.hedr.fileType = 0
        elif self.isEsm(): tes3.hedr.fileType = 1
        elif self.isEss(): tes3.hedr.fileType = 32
        for master in masters:
            tes3.masters.append((master,modInfos[master].size))
        tes3.hedr.setChanged()
        tes3.setChanged()
        #--Write it
        path = os.path.join(self.dir,self.name)
        out = file(path,'wb')
        tes3.getSize()
        tes3.dump(out)
        out.close()
        self.setMTime(mtime)

    def writeHedr(self):
        """Writes hedr subrecord to file, overwriting old hedr."""
        path = os.path.join(self.dir,self.name)
        out = file(path,'r+b')
        out.seek(16) #--Skip to Hedr record data
        self.tes3.hedr.getSize()
        self.tes3.hedr.dump(out)
        out.close()
        #--Done
        self.getHeader()
        self.setMTime()

    def writeDescription(self,description):
        """Sets description to specified text and then writes hedr."""
        description = description[:min(255,len(description))]
        self.tes3.hedr.description = description
        self.tes3.hedr.setChanged()
        self.writeHedr()

    def writeAuthor(self,author):
        """Sets author to specified text and then writes hedr."""
        author = author[:min(32,len(author))]
        self.tes3.hedr.author = author
        self.tes3.hedr.setChanged()
        self.writeHedr()

    def writeAuthorWM(self):
        """Marks author field with " [wm]" to indicate Mash modification."""
        author = self.tes3.hedr.author
        if '[wm]' not in author and len(author) <= 27:
            self.writeAuthor(author+' [wm]')

    def setMTime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = mtime or self.mtime
        path = os.path.join(self.dir,self.name)
        os.utime(path,(time.time(),mtime))
        self.mtime = getmtime(path)
    
    def makeBackup(self, forceBackup=False):
        if self.madeBackup and not forceBackup: return
        #--Backup Directory
        backupDir = os.path.join(self.dir,settings['mosh.fileInfo.backupDir'])
        if not os.path.exists(backupDir): os.makedirs(backupDir)
        #--File Path
        original = os.path.join(self.dir,self.name)
        #--Backup
        backup = os.path.join(backupDir,self.name)
        shutil.copy(original,backup)
        #--First backup
        firstBackup = backup+'f'
        if not os.path.exists(firstBackup):
            shutil.copy(original,firstBackup)
        #--Done
        self.madeBackup = True
    
    def getStats(self):
        stats = self.stats = {}
        path = os.path.join(self.dir,self.name)
        ins = Tes3Reader(self.name,file(path,'rb'))
        while not ins.atEnd():
            #--Get record info and handle it
            (type,size,delFlag,recFlag) = ins.unpackRecHeader()
            if type not in stats: 
                stats[type] = (1,size)
            else:
                count, cumSize = stats[type]
                stats[type] = (count+1, cumSize+size+16) #--16B in header
            #--Seek to next record
            ins.seek(size,1,'Record')
        #--Done
        ins.close()
        
    #--Snapshot Parameters
    def getNextSnapshot(self):
        destDir = os.path.join(self.dir,settings['mosh.fileInfo.snapshotDir'])
        if not os.path.exists(destDir): os.makedirs(destDir)
        (root,ext) = os.path.splitext(self.name)
        destName = root+'-00'+ext
        separator = '-'
        snapLast = ['00']
        #--Look for old snapshots.
        reSnap = re.compile('^'+root+'-([0-9\.]*[0-9]+)'+ext+'$')
        for fileName in os.listdir(destDir):
            maSnap = reSnap.match(fileName)
            if not maSnap: continue
            snapNew = maSnap.group(1).split('.')
            #--Compare shared version numbers
            sharedNums = min(len(snapNew),len(snapLast))
            for index in range(sharedNums):
                (numNew,numLast) = (int(snapNew[index]),int(snapLast[index]))
                if numNew > numLast:
                    snapLast = snapNew
                    continue
            #--Compare length of numbers
            if len(snapNew) > len(snapLast):
                snapLast = snapNew
                continue
        #--New
        snapLast[-1] = ('%0'+`len(snapLast[-1])`+'d') % (int(snapLast[-1])+1,)
        destName = root+separator+('.'.join(snapLast))+ext
        wildcard = root+'*'+ext
        wildcard = _('%s Snapshots|%s|All Snapshots|*.esp;*.esm;*.ess') % (root,wildcard)
        return (destDir,destName,wildcard)

#------------------------------------------------------------------------------
class FileInfos:
    def __init__(self,dir,factory=FileInfo):
        """Init with specified directory and specified factory type."""
        self.dir = dir
        self.factory=factory
        self.data = {}
        self.table = Table(os.path.join(self.dir,'Mash','Table.pkl'))
        self.corrupted = {} #--errorMessage = corrupted[fileName]

    #--Dictionary Emulation
    def __contains__(self,key):
        """Dictionary emulation."""
        return key in self.data
    def __getitem__(self,key):
        """Dictionary emulation."""
        return self.data[key]
    def __setitem__(self,key,value):
        """Dictionary emulation."""
        self.data[key] = value
    def __delitem__(self,key):
        """Dictionary emulation."""
        del self.data[key]
    def keys(self):
        """Dictionary emulation."""
        return self.data.keys()
    def has_key(self,key):
        """Dictionary emulation."""
        return self.data.has_key(key)
    def get(self,key,default):
        """Dictionary emulation."""
        return self.data.get(key,default)

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            fileInfo = self.factory(self.dir,fileName)
            fileInfo.getHeader()
            self.data[fileName] = fileInfo
        except Tes3Error, error:
            self.corrupted[fileName] = error.message
            if fileName in self.data:
                del self.data[fileName]
            raise

    #--Refresh
    def refresh(self):
        data = self.data
        oldList = data.keys()
        newList = []
        added = []
        updated = []
        deleted = []
        if not os.path.exists(self.dir): os.makedirs(self.dir)
        #--Loop over files in directory
        for fileName in os.listdir(self.dir):
            fileName = unicode(fileName, sys.getfilesystemencoding())
            #--Right file type?
            filePath = os.path.join(self.dir,fileName)
            if not os.path.isfile(filePath) or not self.rightFileType(fileName): 
                continue
            fileInfo = self.factory(self.dir,fileName)
            #--New file?
            if fileName not in oldList:
                try:
                    fileInfo.getHeader()
                #--Bad header?
                except Tes3Error, error:
                    self.corrupted[fileName] = error.message
                    continue
                #--Good header?
                else:
                    if fileName in self.corrupted:
                        del self.corrupted[fileName]
                    added.append(fileName)
                    data[fileName] = fileInfo
            #--Updated file?
            elif not fileInfo.sameAs(data[fileName]):
                try:
                    fileInfo.getHeader()
                    data[fileName] = fileInfo
                #--Bad header?
                except Tes3Error, error:
                    self.corrupted[fileName] = error.message
                    del self.data[fileName]
                    continue
                #--Good header?
                else:
                    if fileName in self.corrupted:
                        del self.corrupted[fileName]
                    updated.append(fileName)
            #--No change?
            newList.append(fileName)
        #--Any files deleted?
        for fileName in oldList:
            if fileName not in newList:
                deleted.append(fileName)
                del self.data[fileName]
        #--Return
        return (len(added) or len(updated) or len(deleted))

    #--Right File Type? [ABSTRACT]
    def rightFileType(self,fileName):
        """Bool: filetype (extension) is correct for subclass. [ABSTRACT]"""
        raise AbstractError

    #--Rename
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        #--Update references
        fileInfo = self[oldName]
        self[newName] = self[oldName]
        del self[oldName]
        self.table.moveRow(oldName,newName)
        #--FileInfo
        fileInfo.name = newName
        #--File system
        newPath = os.path.join(fileInfo.dir,newName)
        oldPath = os.path.join(fileInfo.dir,oldName)
        renameFile(oldPath,newPath)
        #--Done
        fileInfo.madeBackup = False

    #--Delete
    def delete(self,fileName):
        """Deletes member file."""
        fileInfo = self[fileName]
        #--File
        filePath = os.path.join(fileInfo.dir,fileInfo.name)
        os.remove(filePath)
        #--Table
        self.table.delRow(fileName)
        #--Misc. Editor backups
        for ext in ('.bak','.tmp','.old'):
            backPath = filePath + ext
            if os.path.exists(backPath): os.remove(backPath)
        #--Backups
        backRoot = os.path.join(fileInfo.dir,settings['mosh.fileInfo.backupDir'],fileInfo.name)
        for backPath in (backRoot,backRoot+'f'):
            if os.path.exists(backPath): os.remove(backPath)
        self.refresh()

    #--Move Exists
    def moveIsSafe(self,fileName,destDir):
        """Bool: Safe to move file to destDir."""
        return not os.path.exists(os.path.join(destDir,fileName))

    #--Move
    def move(self,fileName,destDir):
        """Moves member file to destDir. Will overwrite!"""
        if not os.path.exists(destDir): 
            os.makedirs(destDir)
        srcPath = os.path.join(self.dir,fileName)
        destPath = os.path.join(destDir,fileName)
        renameFile(srcPath,destPath)
        self.refresh()

    #--Copy
    def copy(self,fileName,destDir,destName=None,setMTime=False):
        """Copies member file to destDir. Will overwrite!"""
        if not os.path.exists(destDir): 
            os.makedirs(destDir)
        if not destName: destName = fileName
        srcPath = os.path.join(self.dir,fileName)
        destPath = os.path.join(destDir,destName)
        if os.path.exists(destPath): 
            os.remove(destPath)
        shutil.copyfile(srcPath,destPath)
        if setMTime:
            mtime = getmtime(srcPath)
            os.utime(destPath,(time.time(),mtime))
        self.refresh()

#------------------------------------------------------------------------------
class ModInfo(FileInfo):
    def isWellOrdered(self):
        return not modInfos.doubleTime[self.mtime]

    def isExOverLoaded(self):
        """True if belongs to an exclusion group that is overloaded."""
        maExGroup = reExGroup.match(self.name)
        if not (mwIniFile.isLoaded(self.name) and maExGroup):
            return False
        else:
            return (maExGroup.group(1) in mwIniFile.exOverLoaded)

    def setMTime(self,mtime=0):
        """Sets mtime. Defaults to current value (i.e. reset)."""
        mtime = mtime or self.mtime
        FileInfo.setMTime(self,mtime)
        modInfos.mtimes[self.name] = mtime
    
#------------------------------------------------------------------------------
class ResourceReplacer:
    """Resource Replacer. Used to apply and remove a set of resource (texture, etc.) replacement files."""
    #--Class data
    textureExts = set(['.dds','.tga','.bmp'])
    dirExts = {
        'bookart':  textureExts,
        'fonts':    set(['.fnt','.tex']),
        'icons':    textureExts,
        'meshes':   set(['.nif','.kf']),
        'music':    set(['.mp3']),
        'sound':    set(['.wav']),
        'splash':   textureExts,
        'textures': textureExts,
        }

    def __init__(self,replacerDir,file):
        """Initialize"""
        self.replacerDir = replacerDir
        self.file = file
        self.progress = None
        self.cumSize = 0

    def isApplied(self):
        """Returns True if has been applied."""
        return self.file in settings['mosh.resourceReplacer.applied']
    
    def apply(self,progress=None):
        """Copy files to appropriate resource directories (Textures, etc.).""" 
        if progress:
            self.progress = progress
            self.cumSize = 0
            self.totSize = 0
            self.doRoot(self.sizeDir)
            self.progress.setMax(self.totSize)
        self.doRoot(self.applyDir)
        settings.getChanged('mosh.resourceReplacer.applied').append(self.file)
        self.progress = None

    def remove(self):
        """Uncopy files from appropriate resource directories (Textures, etc.).""" 
        self.doRoot(self.removeDir)
        settings.getChanged('mosh.resourceReplacer.applied').remove(self.file)

    def doRoot(self,action):
        """Copy/uncopy files to/from appropriate resource directories."""
        #--Root directory is Textures directory?
        dirExts = ResourceReplacer.dirExts
        textureExts = ResourceReplacer.textureExts
        srcDir = os.path.join(self.replacerDir,self.file)
        destDir = modInfos.dir
        isTexturesDir = True #--Assume true for now.
        for srcFile in os.listdir(srcDir):
            srcPath  = os.path.join(srcDir,srcFile)
            if os.path.isdir(srcPath) and srcFile.lower() in dirExts:
                isTexturesDir = False
                destPath = os.path.join(destDir,srcFile)
                action(srcPath,destPath,dirExts[srcFile.lower()])
        if isTexturesDir:
            destPath = os.path.join(destDir,'Textures')
            action(srcDir,destPath,textureExts)
    
    def sizeDir(self,srcDir,destDir,exts):
        """Determine cumulative size of files to copy.""" 
        for srcFile in os.listdir(srcDir):
            srcExt = os.path.splitext(srcFile)[-1].lower()
            srcPath  = os.path.join(srcDir,srcFile)
            destPath = os.path.join(destDir,srcFile)
            if srcExt in exts:
                self.totSize += os.path.getsize(srcPath)
            elif os.path.isdir(srcPath):
                self.sizeDir(srcPath,destPath,exts)
    
    def applyDir(self,srcDir,destDir,exts):
        """Copy files to appropriate resource directories (Textures, etc.).""" 
        for srcFile in os.listdir(srcDir):
            srcExt = os.path.splitext(srcFile)[-1].lower()
            srcPath  = os.path.join(srcDir,srcFile)
            destPath = os.path.join(destDir,srcFile)
            if srcExt in exts:
                if not os.path.exists(destDir):
                    os.makedirs(destDir)
                shutil.copyfile(srcPath,destPath)
                if self.progress: 
                    self.cumSize += os.path.getsize(srcPath)
                    self.progress(self.cumSize,_('Copying Files...'))
            elif os.path.isdir(srcPath):
                self.applyDir(srcPath,destPath,exts)
    
    def removeDir(self,srcDir,destDir,exts):
        """Uncopy files from appropriate resource directories (Textures, etc.).""" 
        for srcFile in os.listdir(srcDir):
            srcExt = os.path.splitext(srcFile)[-1].lower()
            srcPath  = os.path.join(srcDir,srcFile)
            destPath = os.path.join(destDir,srcFile)
            if os.path.exists(destPath):
                if srcExt in exts:
                    os.remove(destPath)
                elif os.path.isdir(srcPath):
                    self.removeDir(srcPath,destPath,exts)

#------------------------------------------------------------------------------
class ModInfos(FileInfos):
    #--Init
    def __init__(self,dir,factory=ModInfo):
        FileInfos.__init__(self,dir,factory)
        self.resetMTimes = settings['mosh.modInfos.resetMTimes']
        self.mtimes = self.table.getColumn('mtime')
        self.mtimesReset = [] #--Files whose mtimes have been reset.
        self.doubleTime = {}
        self.objectMaps = None

    #--Refresh File
    def refreshFile(self,fileName):
        try:
            FileInfos.refreshFile(self,fileName)
        finally:
            self.refreshDoubleTime()

    #--Refresh
    def refresh(self):
        hasChanged = FileInfos.refresh(self)
        if hasChanged: 
            #--Reset MTimes?
            if self.resetMTimes:
                self.refreshMTimes()
            #--Any load files disappeared?
            for loadFile in mwIniFile.loadFiles[:]:
                if loadFile not in self.data:
                    self.unload(loadFile)
            self.refreshDoubleTime()
        #--Update mwIniLoadOrder
        mwIniFile.loadOrder = modInfos.getLoadOrder(mwIniFile.loadFiles)
        return hasChanged

    def refreshMTimes(self):
        """Remember/reset mtimes of member files."""
        del self.mtimesReset[:]
        for fileName, fileInfo in self.data.items():
            oldMTime = self.mtimes.get(fileName,fileInfo.mtime)
            self.mtimes[fileName] = oldMTime
            #--Reset mtime?
            if fileInfo.mtime != oldMTime and oldMTime != -1:
                fileInfo.setMTime(oldMTime)
                self.mtimesReset.append(fileName)

    def refreshDoubleTime(self):
        """Refresh doubletime dictionary."""
        doubleTime = self.doubleTime
        doubleTime.clear()
        for modInfo in self.data.values():
            mtime = modInfo.mtime
            doubleTime[mtime] = doubleTime.has_key(mtime)
        #--Refresh MWIni File too
        mwIniFile.refreshDoubleTime()

    def rightFileType(self,fileName):
        """Bool: File is a mod."""
        fileExt = fileName[-4:].lower()
        return (fileExt == '.esp' or fileExt == '.esm')

    def getVersion(self,fileName):
        """Extracts and returns version number for fileName from tes3.hedr.description."""
        if not fileName in self.data or not self.data[fileName].tes3:
            return ''
        maVersion = reVersion.search(self.data[fileName].tes3.hedr.description)
        return (maVersion and maVersion.group(2)) or ''

    #--Circular Masters
    def circularMasters(self,stack,masters=None):
        stackTop = stack[-1]
        masters = masters or (stackTop in self.data and self.data[stackTop].masterNames)
        if not masters: return False
        for master in masters:
            if master in stack: 
                return True
            if self.circularMasters(stack+[master]):
                return True
        return False

    #--Get load order
    def getLoadOrder(self,modNames,asTuple=True):
        """Sort list of mod names into their load order. ASSUMES MODNAMES ARE UNIQUE!!!"""
        data = self.data
        modNames = list(modNames) #--Don't do an in-place sort.
        modNames.sort()
        modNames.sort(key=lambda a: (a in data) and data[a].mtime) #--Sort on modified
        modNames.sort(key=lambda a: a[-1].lower()) #--Sort on esm/esp
        #--Match Bethesda's esm sort order
        #  - Start with masters in chronological order.
        #  - For each master, if it's masters (mm's) are not already in list, 
        #    then place them ahead of master... but in REVERSE order. E.g., last
        #    grandmaster will be first to be added.
        def preMaster(modName,modDex):
            """If necessary, move grandmasters in front of master -- but in 
            reverse order."""
            if self.data.has_key(modName):
                mmNames = list(self.data[modName].masterNames[:])
                mmNames.reverse()
                for mmName in mmNames:
                    if mmName in modNames:
                        mmDex = modNames.index(mmName)
                        #--Move master in front and pre-master it too.
                        if mmDex > modDex:
                            del modNames[mmDex]
                            modNames.insert(modDex,mmName)
                            modDex = 1 + preMaster(mmName,modDex)
            return modDex
        #--Read through modNames.
        modDex = 1
        while modDex < len(modNames):
            modName = modNames[modDex]
            if modName[-1].lower() != 'm': break
            if self.circularMasters([modName]):
                modDex += 1
            else:
                modDex = 1 + preMaster(modName,modDex)
        #--Convert? and return
        if asTuple:
            return tuple(modNames)
        else:
            return modNames

    #--Loading
    def isLoaded(self,fileName):
        """True if fileName is in the the load list."""
        return mwIniFile.isLoaded(fileName)

    def load(self,fileName,doSave=True):
        """Adds file to load list."""
        #--Load masters
        modFileNames = self.keys()
        for master,size in self[fileName].tes3.masters:
            if master in modFileNames and master != fileName:
                self.load(master,False)
        #--Load self
        mwIniFile.load(fileName,doSave)
    
    def unload(self,fileName,doSave=True):
        """Removes file from load list."""
        #--Unload fileName
        mwIniFile.unload(fileName,False)
        #--Unload fileName's children
        loadFiles = mwIniFile.loadFiles[:]
        for loadFile in loadFiles:
            #--Already unloaded? (E.g., grandchild)
            if not mwIniFile.isLoaded(loadFile): continue
            if loadFile not in self.data: continue #--Can happen if user does an external delete.
            #--One of loadFile's masters?
            for master in self[loadFile].tes3.masters:
                if master[0] == fileName:
                    self.unload(loadFile,False)
                    break
        #--Save
        if doSave: mwIniFile.safeSave()

    #--Rename
    def rename(self,oldName,newName):
        """Renames member file from oldName to newName."""
        isLoaded = self.isLoaded(oldName)
        if isLoaded: self.unload(oldName)
        FileInfos.rename(self,oldName,newName)
        self.refreshDoubleTime()
        if isLoaded: self.load(newName)

    #--Delete
    def delete(self,fileName):
        """Deletes member file."""
        self.unload(fileName)
        FileInfos.delete(self,fileName)

    #--Move
    def move(self,fileName,destDir):
        """Moves member file to destDir."""
        self.unload(fileName)
        FileInfos.move(self,fileName,destDir)
    
    #--Resource Replacers -----------------------------------------------------
    def getResourceReplacers(self):
        """Returns list of ResourceReplacer objects for subdirectories of Replacers directory."""
        replacers = {}
        replacerDir = os.path.join(self.dir,'Replacers')
        if not os.path.exists(replacerDir):
            return replacers
        if 'mosh.resourceReplacer.applied' not in settings:
            settings['mosh.resourceReplacer.applied'] = []
        for name in os.listdir(replacerDir):
            path = os.path.join(replacerDir,name)
            if os.path.isdir(path):
                replacers[name] = ResourceReplacer(replacerDir,name)
        return replacers

    #--Object Maps ------------------------------------------------------------
    def addObjectMap(self,fromMod,toMod,objectMap):
        """Add an objectMap with key(fromMod,toMod)."""
        if self.objectMaps == None: self.loadObjectMaps()
        self.objectMaps[(fromMod,toMod)] = objectMap

    def removeObjectMap(self,fromMod,toMod):
        """Deletes objectMap with key(fromMod,toMod)."""
        if self.objectMaps == None: self.loadObjectMaps()
        del self.objectMaps[(fromMod,toMod)]

    def getObjectMap(self,fromMod,toMod):
        """Returns objectMap with key(fromMod,toMod)."""
        if self.objectMaps == None: self.loadObjectMaps()
        return self.objectMaps.get((fromMod,toMod),None)

    def getObjectMaps(self,toMod):
        """Return a dictionary of ObjectMaps with fromMod key for toMod."""
        if self.objectMaps == None: self.loadObjectMaps()
        subset = {}
        for key in self.objectMaps.keys():
            if key[1] == toMod:
                subset[key[0]] = self.objectMaps[key]
        return subset

    def loadObjectMaps(self):
        """Load ObjectMaps from file."""
        path = os.path.join(self.dir,settings['mosh.modInfos.objectMaps'])
        if os.path.exists(path):
            self.objectMaps = compat.uncpickle(open(path,'rb'))
        else:
            self.objectMaps = {}

    def saveObjectMaps(self):
        """Save ObjectMaps to file."""
        if self.objectMaps == None: return
        path = os.path.join(self.dir,settings['mosh.modInfos.objectMaps'])
        outDir = os.path.split(path)[0]
        if not os.path.exists(outDir): os.makedirs(outDir)
        cPickle.dump(self.objectMaps,open(path,'wb'),2)

#------------------------------------------------------------------------------
class ReplJournalDate:
    """Callable: Adds <hr>before journal date."""
    def __init__(self):
        self.prevDate = None

    def __call__(self,mo):
        prevDate = self.prevDate
        newDate = mo.group(1)
        if newDate != prevDate:
            hr = prevDate and '<hr>' or ''
            self.prevDate = newDate
            return '%s<FONT COLOR="9F0000"><B>%s</B></FONT><BR>' % (hr,newDate)
        else:
            return ''

#------------------------------------------------------------------------------
class SaveInfo(FileInfo):
    """Representation of a savegame file."""

    def getStatus(self):
        """Returns the status, i.e., "health" level of the savegame. Based on
        status/health of masters, plus synchronization with current load list."""
        status = FileInfo.getStatus(self)
        masterOrder = self.masterOrder
        #--File size?
        if status > 0 or len(masterOrder) > len(mwIniFile.loadOrder):
            return status
        #--Current ordering?
        if masterOrder != mwIniFile.loadOrder[:len(masterOrder)]: 
            return status
        elif masterOrder == mwIniFile.loadOrder: 
            return -20
        else:
            return -10

    def getJournal(self):
        """Returns the text of the journal from the savegame in slightly 
        modified html format."""
        if 'journal' in self.extras: 
            return self.extras['journal']
        #--Default 
        self.extras['journal'] = _('[No Journal Record Found.]')
        #--Open save file and look for journal entry
        inPath = os.path.join(self.dir,self.name)
        ins = Tes3Reader(self.name,file(inPath,'rb'))
        #--Raw data read
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            if name != 'JOUR':
                ins.seek(size,1,name)
            #--Journal
            else:
                (subName,subSize) = ins.unpackSubHeader('JOUR')
                if subName != 'NAME':
                    self.extras['journal'] == _('[Error reading file.]')
                else:
                    reDate = re.compile(r'<FONT COLOR="9F0000">(.+?)</FONT><BR>')
                    reTopic = re.compile(r'@(.*?)#')
                    data = ins.read(subSize)
                    data = reDate.sub(ReplJournalDate(),data)
                    data = reTopic.sub(r'\1',data)
                    self.extras['journal'] = cstrip(data)
                break
        #--Done
        ins.close()
        print self.extras['journal']
        return self.extras['journal']

    def getScreenshot(self):
        """Returns screenshot data with alpha info stripped out.
        If screenshot data isn't available, returns None."""
        #--Used cached screenshot, if have it.
        if 'screenshot' in self.extras:
            return self.extras['screenshot']
        #--Gets tes3 header
        path = os.path.join(self.dir,self.name)
        try:
            ins = Tes3Reader(self.name,file(path,'rb'))
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            if name != 'TES3': raise Tes3Error(self.name,_('Expected TES3, but got ')+name)
            self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        except struct.error, rex:
            ins.close()
            raise Tes3Error(self.name,'Struct.error: '+`rex`)
        except Tes3Error, error:
            ins.close()
            error.inName = self.name
            raise
        ins.close()
        #--Get screenshot data subrecord
        for subrecord in self.tes3.others:
            if subrecord.name == 'SCRS':
                #--Convert bgra array to rgb array
                buff = cStringIO.StringIO()
                for num in xrange(len(subrecord.data)/4):
                    bb,gg,rr = struct.unpack('3B',subrecord.data[num*4:num*4+3])
                    buff.write(struct.pack('3B',rr,gg,bb))
                rgbString = buff.getvalue()
                #--Image processing (brighten, increase range)
                rgbArray = array.array('B',rgbString)
                rgbAvg   = float(sum(rgbArray))/len(rgbArray)
                rgbSqAvg = float(sum(xx*xx for xx in rgbArray))/len(rgbArray)
                rgbSigma = math.sqrt(rgbSqAvg - rgbAvg*rgbAvg)
                rgbScale = max(1.0,80/rgbSigma)
                #print '%s\t%f.2\t%f.2' % (self.name,rgbAvg,rgbSigma)
                def remap(color):
                    color = color - rgbAvg
                    color = color * rgbScale
                    return max(0,min(255,int(color+128)))
                buff.seek(0)
                for num,char in enumerate(rgbString):
                    buff.write(struct.pack('B',remap(ord(char))))
                screenshot = buff.getvalue()
                buff.close()
                break
        else: #--No SCRS data
            screenshot = None
        #--Cache and return
        self.extras['screenshot'] = screenshot
        return screenshot

#------------------------------------------------------------------------------
class SaveInfos(FileInfos):
    """Collection of saveInfos for savefiles in the saves directory."""
    #--Init
    def __init__(self,dir,factory=SaveInfo):
        FileInfos.__init__(self,dir,factory)

    #--Right File Type (Used by Refresh)
    def rightFileType(self,fileName):
        return (fileName[-4:].lower() == '.ess')

#------------------------------------------------------------------------------
class ResPack:
    """Resource package (BSA or resource replacer). This is the abstract supertype."""

    def getOrder(self):
        """Returns load order number or None if not loaded."""
        raise AbstractError
    def rename(self,newName):
        """Renames respack."""
        raise AbstractError
    def duplicate(self,newName):
        """Duplicates self with newName."""
        raise AbstractError
    def select(self):
        """Selects package."""
        raise AbstractError
    def unselect(self):
        """Unselects package."""
        raise AbstractError
    def isSelected(self):
        """Returns True if is currently selected."""
        raise AbstractError

#------------------------------------------------------------------------------
class BSAPack(ResPack):
    """BSA file resource package."""
    pass

#------------------------------------------------------------------------------
class ResReplacerPack(ResPack):
    """Resource replacer directory."""
    pass

#------------------------------------------------------------------------------
class ResPacks:
    """Collection of Res Packs (BSAs and Resource Replacers)."""
    def __init__(self):
        """Initialize. Get BSA and resource replacers."""
        self.data = {}
        self.refresh()

    def refresh(self):
        """Refreshes BSA and resource replacers."""
        raise UncodedError

#------------------------------------------------------------------------------
# UtilsData
#-# D.C.-G
#
# for UtilsPanel extension.
#
utilsCommands = ("mish",)
class UtilsData(DataDict): 
    def __init__(self):
        """Initialize."""
        self.dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of utilities."""
        self.dir = dirs['app']
        #-# Since there is only one utils file, its name is hardcoded.
        utilsFile = "utils.dcg"
        newData = {}
        if os.path.isfile(utilsFile) and os.access(utilsFile, os.R_OK):
            f = open(utilsFile, "r")
            lines = f.readlines()
            f.close()
            for line in lines:
                line = line.strip()
                if line.startswith(";") == False and line != "":
                    name, commandLine, arguments, description = line.split(";")
                    newData[name] = (commandLine.strip(), arguments, description.strip())
        changed = (self.data != newData)
        self.data = newData
        return changed

    def delete(self,fileName):
        """Deletes member file."""
        filePath = self.dir.join(fileName)
        filePath.remove()
        del self.data[fileName]

    def save(self):
        """Writes the file on the disk."""
        utilsFile = "utils.dcg"
        orgData = {}
        lines = []
        if os.path.isfile(utilsFile) and os.access(utilsFile, os.R_OK):
            f = open(utilsFile, "r")
            lines = f.readlines()
            f.close()
            for line in lines:
                line = line.strip()
                if line.startswith(";") == False and line != "":
                    name, commandLine, arguments, description = line.split(";")
                    orgData[name] = (commandLine.strip(), arguments, description.strip())
        changed = (self.data != orgData)
        if changed:
            # items suppresed
            lns = lines
            for key in orgData.keys():
                if key not in self.data.keys():
                    for line in lns:
                        if line .startswith(key):
                            lines.remove(line)
            # items added or modified
            for key, value in self.data.iteritems():
                val = list(value)
                if val[0] not in utilsCommands: val[0] = '"'+val[0].strip(""" '\t"\n\r\x00""")+'"'
                val = tuple(val)
                if key not in orgData.keys():
                    lines.append("%s;%s;%s;%s\n"%((key,) + value))
                elif key in orgData.keys() and value != orgData[key]:
                    for line in lines:
                        if line.startswith(key):
                            idx = lines.index(line)
                            lines[idx] = "%s;%s;%s;%s\n"%((key,) + value)
            f = open(utilsFile, "w")
            f.writelines(lines)
            f.close()

#------------------------------------------------------------------------------
class ScreensData(DataDict): 
    def __init__(self):
        """Initialize."""
        self.dir = dirs['app']
        self.data = {} #--data[Path] = (ext,mtime)

    def refresh(self):
        """Refresh list of screenshots."""
        self.dir = dirs['app']
        ssBase = GPath(mwIniFile.getSetting('General','Screen Shot Base Name','ScreenShot'))
        if ssBase.head:
            self.dir = self.dir.join(ssBase.head)
        newData = {}
        reImageExt = re.compile(r'\.(bmp|jpg)$',re.I)
        #--Loop over files in directory
        for fileName in self.dir.list():
            filePath = self.dir.join(fileName)
            maImageExt = reImageExt.search(fileName.s)
            if maImageExt and filePath.isfile(): 
                newData[fileName] = (maImageExt.group(1).lower(),filePath.mtime)
        changed = (self.data != newData)
        self.data = newData
        return changed

    def delete(self,fileName):
        """Deletes member file."""
        filePath = self.dir.join(fileName)
        filePath.remove()
        del self.data[fileName]

# Installers ------------------------------------------------------------------
#------------------------------------------------------------------------------
class Installer(object):
    """Object representing an installer archive, its user configuration, and 
    its installation state."""

    #--Member data
    persistent = ('archive','order','group','modified','size','crc',   
        'fileSizeCrcs','type','isActive','subNames','subActives','dirty_sizeCrc',
        'comments','readMe','packageDoc','packagePic','src_sizeCrcDate','hasExtraData',
        'skipVoices','espmNots')
    volatile = ('data_sizeCrc','skipExtFiles','skipDirFiles','status','missingFiles',
        'mismatchedFiles','refreshed','mismatchedEspms','unSize','espms','underrides')
    __slots__ = persistent+volatile
    #--Package analysis/porting.
    docDirs = set(('screenshots',))
    dataDirs = set(('bookart','docs','fonts','icons','meshes','music','shaders', 'sound','splash','textures','video','mash plus','mits'))
    dataDirsPlus = dataDirs | set()
    dataDirsMinus = set(('mash','replacers','distantland','clean','mwse')) #--Will be skiped even if hasExtraData == True.
    reDataFile = re.compile(r'\.(esp|esm|bsa)$',re.I)
    reReadMe = re.compile(r'^([^\\]*)(dontreadme|read[ _]?me|lisez[ _]?moi)([^\\]*)\.(txt|rtf|htm|html|doc|odt)$',re.I)
    skipExts = set(('.dll','.dlx','.exe','.py','.pyc','.7z','.zip','.rar','.db'))
    docExts = set(('.txt','.rtf','.htm','.html','.doc','.odt','.jpg','.png','.pdf','.css','.xls'))
    #--Temp Files/Dirs
    tempDir = GPath('InstallerTemp')
    tempList = GPath('InstallerTempList.txt')
    #--Aliases
    off_local = {}

    #--Class Methods ----------------------------------------------------------
    @staticmethod
    def getGhosted():
        """Returns map of real to ghosted files in mods directory."""
        dataDir = dirs['mods']
        ghosts = [x for x in dataDir.list() if x.cs[-6:] == '.ghost']
        return dict((x.root,x) for x in ghosts if not dataDir.join(x).root.exists())

    @staticmethod
    def clearTemp():
        """Clear temp install directory -- DO NOT SCREW THIS UP!!!"""
        Installer.tempDir.rmtree(safety='Temp')

    @staticmethod
    def sortFiles(files):
        """Utility function. Sorts files by directory, then file name."""
        def sortKey(file):
            dirFile = file.lower().rsplit('\\',1)
            if len(dirFile) == 1: dirFile.insert(0,'')
            return dirFile
        sortKeys = dict((x,sortKey(x)) for x in files)
        return sorted(files,key=lambda x: sortKeys[x])

    @staticmethod
    def refreshSizeCrcDate(apRoot,old_sizeCrcDate,progress=None,removeEmpties=False,fullRefresh=False):
        """Update old_sizeCrcDate for root directory. 
        This is used both by InstallerProject's and by InstallersData."""
        rootIsMods = (apRoot == dirs['mods']) #--Filtered scanning for mods directory.
        norm_ghost = (rootIsMods and Installer.getGhosted()) or {}
        ghost_norm = dict((y,x) for x,y in norm_ghost.iteritems())
        rootName = apRoot.stail
        progress = progress or bolt.Progress()
        new_sizeCrcDate = {}
        bethFiles = bush.bethDataFiles
        skipExts = Installer.skipExts
        asRoot = apRoot.s
        relPos = len(apRoot.s)+1
        pending = set()
        #--Scan for changed files
        progress(0,_("%s: Pre-Scanning...") % rootName)
        progress.setFull(1)
        dirDirsFiles = []
        emptyDirs = set()
        for asDir,sDirs,sFiles in os.walk(asRoot):
            progress(0.05,_("%s: Pre-Scanning...\n%s") % (rootName,asDir[relPos:]))
            if rootIsMods and asDir == asRoot:
                sDirs[:] = [x for x in sDirs if x.lower() not in Installer.dataDirsMinus]
            dirDirsFiles.append((asDir,sDirs,sFiles))
            if not (sDirs or sFiles): emptyDirs.add(GPath(asDir))
        progress(0,_("%s: Scanning...") % rootName)
        progress.setFull(1+len(dirDirsFiles))
        for index,(asDir,sDirs,sFiles) in enumerate(dirDirsFiles):
            progress(index)
            rsDir = asDir[relPos:]
            inModsRoot = rootIsMods and not rsDir
            apDir = GPath(asDir)
            rpDir = GPath(rsDir)
            for sFile in sFiles:
                #print '...',sFile
                ext = sFile[sFile.rfind('.'):].lower()
                rpFile = rpDir.join(sFile)
                if inModsRoot:
                    if ext in skipExts: continue
                    if not rsDir and sFile.lower() in bethFiles: continue
                    rpFile = ghost_norm.get(rpFile,rpFile)
                isEspm = not rsDir and (ext == '.esp' or ext == '.esm')
                apFile = apDir.join(sFile)
                size = apFile.size
                date = apFile.mtime
                oSize,oCrc,oDate = old_sizeCrcDate.get(rpFile,(0,0,0))
                if size == oSize and (date == oDate or isEspm):
                    new_sizeCrcDate[rpFile] = (oSize,oCrc,oDate)
                else:
                    pending.add(rpFile)
        #--Remove empty dirs?
        if settings['bash.installers.removeEmptyDirs']:
            for dir in emptyDirs: 
                try: dir.removedirs()
                except OSError: pass
        #--Force update?
        if fullRefresh: pending |= set(new_sizeCrcDate)
        changed = bool(pending) or (len(new_sizeCrcDate) != len(old_sizeCrcDate))
        #--Update crcs?
        if pending:
            progress(0,_("%s: Calculating CRCs...\n") % rootName)
            progress.setFull(1+len(pending))
            try:
                us = unicode(rpFile.s, sys.getfilesystemencoding())
            except TypeError:
                us = rpFile.s
            for index,rpFile in enumerate(sorted(pending)):
                string = (_("%s: Calculating CRCs...\n%s") % 
                            (rootName, us)
                         )
                progress(index,string)
                apFile = apRoot.join(norm_ghost.get(rpFile,rpFile))
                crc = apFile.crc
                size = apFile.size
                date = apFile.mtime
                new_sizeCrcDate[rpFile] = (size,crc,date)
        old_sizeCrcDate.clear()
        old_sizeCrcDate.update(new_sizeCrcDate)
        #--Done
        return changed
    
    #--Initization, etc -------------------------------------------------------
    def initDefault(self):
        """Inits everything to default values."""
        #--Package Only
        self.archive = ''
        self.modified = 0 #--Modified date
        self.size = 0 #--size of archive file
        self.crc = 0 #--crc of archive
        self.type = 0 #--Package type: 0: unset/invalid; 1: simple; 2: complex
        self.fileSizeCrcs = []
        self.subNames = []
        self.src_sizeCrcDate = {} #--For InstallerProject's
        #--Dirty Update
        self.dirty_sizeCrc = {}
        #--Mixed
        self.subActives = []
        #--User Only
        self.skipVoices = False
        self.hasExtraData = False
        self.comments = ''
        self.group = '' #--Default from abstract. Else set by user.
        self.order = -1 #--Set by user/interface.
        self.isActive = False
        self.espmNots = set() #--Lowercase esp/m file names that user has decided not to install.
        #--Volatiles (unpickled values)
        #--Volatiles: directory specific
        self.refreshed = False
        #--Volatile: set by refreshDataSizeCrc
        self.readMe = self.packageDoc = self.packagePic = None
        self.data_sizeCrc = {}
        self.skipExtFiles = set()
        self.skipDirFiles = set()
        self.espms = set()
        self.unSize = 0
        #--Volatile: set by refreshStatus
        self.status = 0
        self.underrides = set()
        self.missingFiles = set()
        self.mismatchedFiles = set()
        self.mismatchedEspms = set()

    def __init__(self,archive):
        """Initialize."""
        self.initDefault()
        self.archive = archive.stail

    def __getstate__(self):
        """Used by pickler to save object state."""
        getter = object.__getattribute__
        return tuple(getter(self,x) for x in self.persistent)

    def __setstate__(self,values):
        """Used by unpickler to recreate object."""
        self.initDefault()
        setter = object.__setattr__
        for value,attr in zip(values,self.persistent):
            setter(self,attr,value)
        if self.dirty_sizeCrc == None:
            self.dirty_sizeCrc = {} #--Use empty dict instead.
        self.refreshDataSizeCrc()

    def __copy__(self,iClass=None):
        """Create a copy of self -- works for subclasses too (assuming subclasses 
        don't add new data members). iClass argument is to support Installers.updateDictFile"""
        iClass = iClass or self.__class__
        clone = iClass(GPath(self.archive))
        copier = copy.copy
        getter = object.__getattribute__
        setter = object.__setattr__
        for attr in Installer.__slots__:
            setter(clone,attr,copier(getter(self,attr)))
        return clone

    def refreshDataSizeCrc(self):
        """Updates self.data_sizeCr and related variables. 
        Also, returns dest_src map for install operation."""
        if isinstance(self,InstallerArchive):
            archiveRoot = GPath(self.archive).sroot
        else:
            archiveRoot = self.archive
        reReadMe = self.reReadMe
        docExts = self.docExts
        docDirs = self.docDirs
        dataDirsPlus = self.dataDirsPlus
        dataDirsMinus = self.dataDirsMinus
        skipExts = self.skipExts
        bethFiles = bush.bethDataFiles
        packageFiles = set(('package.txt','package.jpg'))
        unSize = 0
        espmNots = self.espmNots
        skipVoices = self.skipVoices
        off_local = self.off_local
        if espmNots and not skipVoices:
            skipEspmVoices = set(x.cs for x in espmNots)
        else:
            skipEspmVoices = None
        skipDistantLOD = settings['bash.installers.skipDistantLOD']
        hasExtraData = self.hasExtraData
        type = self.type
        if type == 2:
            allSubs = set(self.subNames[1:])
            activeSubs = set(x for x,y in zip(self.subNames[1:],self.subActives[1:]) if y)
        #--Init to empty
        self.readMe = self.packageDoc = self.packagePic = None
        for attr in ('skipExtFiles','skipDirFiles','espms'):
            object.__getattribute__(self,attr).clear()
        data_sizeCrc = {}
        skipExtFiles = self.skipExtFiles
        skipDirFiles = self.skipDirFiles
        espms = self.espms
        dest_src = {}
        #--Bad archive?
        if type not in (1,2): return dest_src
        #--Scan over fileSizeCrcs
        for full,size,crc in self.fileSizeCrcs:
            file = full #--Default
            if type == 2: #--Complex archive
                subFile = full.split('\\',1)
                if len(subFile) == 2:
                    sub,file = subFile
                    if sub not in activeSubs:
                        if sub not in allSubs:
                            skipDirFiles.add(file)
                        continue
            rootPos = file.find('\\')
            extPos = file.rfind('.')
            fileLower = file.lower()
            rootLower = (rootPos > 0 and fileLower[:rootPos]) or ''
            fileExt = (extPos > 0 and fileLower[extPos:]) or ''
            #--Skip file?
            if (rootLower == 'omod conversion data' or 
                fileLower[-9:] == 'thumbs.db' or fileLower[-11:] == 'desktop.ini'):
                continue #--Silent skip
            elif skipDistantLOD and fileLower[:10] == 'distantlod':
                continue
            elif skipVoices and fileLower[:11] == 'sound\\voice':
                continue
            elif file in bethFiles:
                skipDirFiles.add(full)
                continue
            elif not hasExtraData and rootLower and rootLower not in dataDirsPlus:
                skipDirFiles.add(full)
                continue
            elif hasExtraData and rootLower and rootLower in dataDirsMinus:
                skipDirFiles.add(full)
                continue
            elif fileExt in skipExts:
                skipExtFiles.add(full)
                continue
            #--Remap (and/or skip)
            dest = file #--Default. May be remapped below.
            #--Esps
            if not rootLower and reModExt.match(fileExt):
                pFile = pDest = GPath(file)
                if pFile in off_local:
                    pDest = off_local[pFile]
                    dest = pDest.s
                espms.add(pDest)
                if pDest in espmNots: continue
            #--Esp related voices (Oblivion)
            elif skipEspmVoices and fileLower[:12] == 'sound\\voice\\':
                farPos = file.find('\\',12)
                if farPos > 12 and fileLower[12:farPos] in skipEspmVoices:
                    continue
            #--Docs
            elif rootLower in docDirs:
                dest = 'Docs\\'+file[rootPos+1:]
            elif not rootLower:
                maReadMe = reReadMe.match(file)
                if file.lower() == 'masterlist.txt':
                    pass
                elif maReadMe:
                    if not (maReadMe.group(1) or maReadMe.group(3)):
                        dest = 'Docs\\%s%s' % (archiveRoot,fileExt)
                    else:
                        dest = 'Docs\\'+file
                    self.readMe = dest
                elif fileLower == 'package.txt':
                    dest = self.packageDoc = 'Docs\\'+archiveRoot+'.package.txt'
                elif fileLower == 'package.jpg':
                    dest = self.packagePic = 'Docs\\'+archiveRoot+'.package.jpg'
                elif fileExt in docExts:
                    dest = 'Docs\\'+file
            #--Save
            key = GPath(dest)
            data_sizeCrc[key] = (size,crc)
            dest_src[key] = full
            unSize += size
        self.unSize = unSize
        (self.data_sizeCrc,old_sizeCrc) = (data_sizeCrc,self.data_sizeCrc)
        #--Update dirty?
        if self.isActive and data_sizeCrc != old_sizeCrc:
            dirty_sizeCrc = self.dirty_sizeCrc
            for file,sizeCrc in old_sizeCrc.iteritems():
                if file not in dirty_sizeCrc and sizeCrc != data_sizeCrc.get(file):
                    dirty_sizeCrc[file] = sizeCrc
        #--Done (return dest_src for install operation)
        return dest_src

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        raise AbstractError

    def refreshBasic(self,archive,progress=None,fullRefresh=False):
        """Extract file/size/crc info from archive."""
        self.refreshSource(archive,progress,fullRefresh)
        def fscSortKey(fsc):
            dirFile = fsc[0].lower().rsplit('\\',1)
            if len(dirFile) == 1: dirFile.insert(0,'')
            return dirFile
        fileSizeCrcs = self.fileSizeCrcs
        sortKeys = dict((x,fscSortKey(x)) for x in fileSizeCrcs)
        fileSizeCrcs.sort(key=lambda x: sortKeys[x])
        #--Type, subNames
        reDataFile = self.reDataFile
        dataDirs = self.dataDirs
        type = 0
        subNameSet = set()
        subNameSet.add('')
        for file,size,crc in fileSizeCrcs:
            fileLower = file.lower()
            if type != 1:
                frags = file.split('\\')
                nfrags = len(frags)
                #--Type 1?
                if (nfrags == 1 and reDataFile.search(frags[0]) or
                    nfrags > 1 and frags[0].lower() in dataDirs):
                    type = 1
                    break
                #--Type 2?
                elif nfrags > 2 and frags[1].lower() in dataDirs:
                    subNameSet.add(frags[0])
                    type = 2
                elif nfrags == 2 and reDataFile.search(frags[1]):
                    subNameSet.add(frags[0])
                    type = 2
        self.type = type
        #--SubNames, SubActives
        if type == 2:
            actives = set(x for x,y in zip(self.subNames,self.subActives) if (y or x == ''))
            self.subNames = sorted(subNameSet,key=string.lower)
            if len(self.subNames) == 2: #--If only one subinstall, then make it active.
                self.subActives = [True,True]
            else:
                self.subActives = [(x in actives) for x in self.subNames]
        else:
            self.subNames = []
            self.subActives = []
        #--Data Size Crc
        self.refreshDataSizeCrc()

    def refreshStatus(self,installers):
        """Updates missingFiles, mismatchedFiles and status.
        Status:
        20: installed (green)
        10: mismatches (yellow)
        0: unconfigured (white)
        -10: missing files (red)
        -20: bad type (grey)
        """
        data_sizeCrc = self.data_sizeCrc
        data_sizeCrcDate = installers.data_sizeCrcDate
        abnorm_sizeCrc = installers.abnorm_sizeCrc
        missing = self.missingFiles
        mismatched = self.mismatchedFiles
        misEspmed = self.mismatchedEspms
        underrides = set()
        status = 0
        missing.clear()
        mismatched.clear()
        misEspmed.clear()
        if self.type == 0:
            status = -20
        elif data_sizeCrc:
            for file,sizeCrc in data_sizeCrc.iteritems():
                sizeCrcDate = data_sizeCrcDate.get(file)
                if not sizeCrcDate:
                    missing.add(file)
                elif sizeCrc != sizeCrcDate[:2]:
                    mismatched.add(file)
                    if not file.shead and reModExt.search(file.s):
                        misEspmed.add(file)
                if sizeCrc == abnorm_sizeCrc.get(file):
                    underrides.add(file)
            if missing: status = -10
            elif misEspmed: status = 10
            elif mismatched: status = 20
            else: status = 30
        #--Clean Dirty
        dirty_sizeCrc = self.dirty_sizeCrc
        for file,sizeCrc in dirty_sizeCrc.items():
            sizeCrcDate = data_sizeCrcDate.get(file)
            if (not sizeCrcDate or sizeCrc != sizeCrcDate[:2] or
                sizeCrc == data_sizeCrc.get(file)
                ):
                del dirty_sizeCrc[file]
        #--Done
        (self.status,oldStatus) = (status,self.status)
        (self.underrides,oldUnderrides) = (underrides,self.underrides)
        return (self.status != oldStatus or self.underrides != oldUnderrides)

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        raise AbstractError

#------------------------------------------------------------------------------
class InstallerMarker(Installer):
    """Represents a marker installer entry. 
    Currently only used for the '==Last==' marker"""
    __slots__ = tuple() #--No new slots

    def __init__(self,archive):
        """Initialize."""
        Installer.__init__(self,archive)
        self.modified = time.time()

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        pass

    def install(self,name,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        pass

#------------------------------------------------------------------------------
class InstallerArchiveError(bolt.BoltError): pass

#------------------------------------------------------------------------------
class InstallerArchive(Installer):
    """Represents an archive installer entry."""
    __slots__ = tuple() #--No new slots

    #--File Operations --------------------------------------------------------
    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        #--Basic file info
        self.modified = archive.mtime
        self.size = archive.size
        self.crc = archive.crc
        #--Get fileSizeCrcs
        fileSizeCrcs = self.fileSizeCrcs = []
        reList = re.compile('(Path|Size|CRC|Attributes) = (.+)')
        file = size = crc = isdir = 0
        ins = os.popen('7z.exe l -slt "%s"' % archive.s,'rt')
        for line in ins:
            line = unicode(line, sys.getfilesystemencoding())
            maList = reList.match(line)
            if maList:
                key,value = maList.groups()
                if key == 'Path': file = value
                elif key == 'Size': size = int(value)
                elif key == 'Attributes': isdir = (value[0] == 'D')
                elif key == 'CRC':
                    crc = int(value,16)
                    if file and not isdir:
                        fileSizeCrcs.append((file,size,crc))
                        #print '%08X %10d %s' % (crc,size,file)
                    file = size = crc = isdir = 0
        result = ins.close()
        if result: 
            raise InstallerArchiveError('Unable to read archive %s (exit:%s).' % (archive.s,result))

    def unpackToTemp(self,archive,fileNames,progress=None):
        """Erases all files from self.tempDir and then extracts specified files 
        from archive to self.tempDir.
        fileNames: File names (not paths)."""
        if not fileNames: raise ArgumentError(_("No files to extract for %s.") % archive.s)
        progress = progress or bolt.Progress()
        progress.state,progress.full = 0,len(fileNames)
        #--Dump file list
        out = self.tempList.open('w')
        out.write('\n'.join(fileNames).encode('utf8'))
        out.close()
        #--Extract files
        self.clearTemp()
        apath = dirs['installers'].join(archive)
        command = '7z.exe x "%s" -y -o%s @%s' % (apath.s, self.tempDir.s, self.tempList.s)
        ins = os.popen(command,'r')
        reExtracting = re.compile('Extracting\s+(.+)')
        extracted = []
        for line in ins:
            maExtracting = reExtracting.match(line)
            if maExtracting: 
                extracted.append(maExtracting.group(1).strip())
                progress.plus()
        result = ins.close()
        if result:
            raise StateError(_("Extraction failed."))
        #ensure that no file is read only
        for thedir, subdirs, files in os.walk(self.tempDir.s):
            for f in files:
                os.chmod(os.path.join(thedir, f),stat.S_IWRITE)
        #--Done
        self.tempList.remove()

    def install(self,archive,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        progress = progress or bolt.Progress()
        destDir = dirs['mods']
        destFiles = set(destFiles)
        norm_ghost = Installer.getGhosted()
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in destFiles)
        if not dest_src: return 0
        #--Extract
        progress(0,archive.s+_("\nExtracting files..."))
        fileNames = [x[0] for x in dest_src.itervalues()]
        self.unpackToTemp(archive,dest_src.values(),SubProgress(progress,0,0.9))
        #--Move
        progress(0.9,archive.s+_("\nMoving files..."))
        count = 0
        tempDir = self.tempDir
        norm_ghost = Installer.getGhosted()
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = tempDir.join(src)
            destFull = destDir.join(norm_ghost.get(dest,dest))
            if srcFull.exists():
                srcFull.moveTo(destFull)
                data_sizeCrcDate[dest] = (size,crc,destFull.mtime)
                count += 1
        self.clearTemp()
        return count

    def unpackToProject(self,archive,project,progress=None):
        """Unpacks archive to build directory."""
        progress = progress or bolt.Progress()
        files = self.sortFiles([x[0] for x in self.fileSizeCrcs])
        if not files: return 0
        #--Clear Project
        destDir = dirs['installers'].join(project)
        if destDir.exists(): destDir.rmtree(safety='Installers')
        #--Extract
        progress(0,project.s+_("\nExtracting files..."))
        self.unpackToTemp(archive,files,SubProgress(progress,0,0.9))
        #--Move
        progress(0.9,project.s+_("\nMoving files..."))
        count = 0
        tempDir = self.tempDir
        for file in files:
            srcFull = tempDir.join(file)
            destFull = destDir.join(file)
            if srcFull.exists():
                srcFull.moveTo(destFull)
                count += 1
        self.clearTemp()
        return count

#------------------------------------------------------------------------------
class InstallerProject(Installer):
    """Represents a directory/build installer entry."""
    __slots__ = tuple() #--No new slots

    def removeEmpties(self,name):
        """Removes empty directories from project directory."""
        empties = set()
        projectDir = dirs['installers'].join(name)
        for asDir,sDirs,sFiles in os.walk(projectDir.s):
            if not (sDirs or sFiles): empties.add(GPath(asDir))
        for empty in empties: empty.removedirs()
        projectDir.makedirs() #--In case it just got wiped out.

    def refreshSource(self,archive,progress=None,fullRefresh=False):
        """Refreshes fileSizeCrcs, size, date and modified from source archive/directory."""
        fileSizeCrcs = self.fileSizeCrcs = []
        src_sizeCrcDate = self.src_sizeCrcDate
        apRoot = dirs['installers'].join(archive)
        Installer.refreshSizeCrcDate(apRoot, src_sizeCrcDate, 
            progress, True, fullRefresh)
        cumDate = 0
        cumSize = 0
        for file in [x.s for x in self.src_sizeCrcDate]:
            size,crc,date = src_sizeCrcDate[GPath(file)]
            fileSizeCrcs.append((file,size,crc))
            cumSize += size
            cumDate = max(cumDate,date)
        self.size = cumSize
        self.modified = cumDate
        self.crc = 0 
        self.refreshed = True

    def install(self,name,destFiles,data_sizeCrcDate,progress=None):
        """Install specified files to Oblivion\Data directory."""
        destDir = dirs['mods']
        destFiles = set(destFiles)
        data_sizeCrc = self.data_sizeCrc
        dest_src = dict((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in destFiles)
        if not dest_src: return 0
        #--Copy Files
        count = 0
        norm_ghost = Installer.getGhosted()
        srcDir = dirs['installers'].join(name)
        for dest,src in dest_src.iteritems():
            size,crc = data_sizeCrc[dest]
            srcFull = srcDir.join(src)
            destFull = destDir.join(norm_ghost.get(dest,dest))
            if srcFull.exists():
                srcFull.copyTo(destFull)
                data_sizeCrcDate[dest] = (size,crc,destFull.mtime)
                count += 1
        return count

    def syncToData(self,package,projFiles):
        """Copies specified projFiles from Oblivion\Data to project directory."""
        srcDir = dirs['mods']
        projFiles = set(projFiles)
        srcProj = tuple((x,y) for x,y in self.refreshDataSizeCrc().iteritems() if x in projFiles)
        if not srcProj: return (0,0)
        #--Sync Files
        updated = removed = 0
        norm_ghost = Installer.getGhosted()
        projDir = dirs['installers'].join(package)
        for src,proj in srcProj:
            srcFull = srcDir.join(norm_ghost.get(src,src))
            projFull = projDir.join(proj)
            if not srcFull.exists():
                projFull.remove()
                removed += 1
            else:
                srcFull.copyTo(projFull)
                updated += 1
        self.removeEmpties(package)
        return (updated,removed)

#------------------------------------------------------------------------------
class InstallersData(bolt.TankData, DataDict):
    """Installers tank data. This is the data source for """
    status_color = {-20:'grey',-10:'red',0:'white',10:'orange',20:'yellow',30:'green'}
    type_textKey = {1:'BLACK',2:'NAVY'}

    def __init__(self):
        """Initialize."""
        self.dir = dirs['installers']
        self.bashDir = self.dir.join('Bash')
        #--Tank Stuff
        bolt.TankData.__init__(self,settings)
        self.tankKey = 'bash.installers'
        self.tankColumns = ['Package','Order','Modified','Size','Files']
        self.title = _('Installers')
        #--Default Params
        self.defaultParam('columns',self.tankColumns)
        self.defaultParam('colWidths',{
            'Package':100,'Package':100,'Order':10,'Group':60,'Modified':60,'Size':40,'Files':20})
        self.defaultParam('colAligns',{'Order':'RIGHT','Size':'RIGHT','Files':'RIGHT','Modified':'RIGHT'})
        #--Persistent data
        self.dictFile = PickleDict(self.bashDir.join('Installers.dat'))
        self.data = {}
        self.data_sizeCrcDate = {}
        #--Volatile
        self.abnorm_sizeCrc = {} #--Normative sizeCrc, according to order of active packages
        self.hasChanged = False
        self.loaded = False
        self.lastKey = GPath('==Last==')
        self.renamedSizeDate = (0,0)

    def addMarker(self, name):
        path = GPath(name)
        self.data[path] = InstallerMarker(path)

    def setChanged(self,hasChanged=True):
        """Mark as having changed."""
        self.hasChanged = hasChanged

    #-# D.C.-G.
    #-# Modified to avoid system error if installers path is not reachable.
    def refresh(self,progress=None,what='DIONS',fullRefresh=False):
        """Refresh info."""
        if not os.access(dirs["installers"].s, os.W_OK): return "noDir"
        progress = progress or bolt.Progress()
        #--MakeDirs
        self.bashDir.makedirs()
        #--Archive invalidation
        if settings.get('bash.bsaRedirection'):
            oblivionIni.setBsaRedirection(True)
        #--Refresh Data
        changed = False
        self.refreshRenamed()
        if not self.loaded: 
            progress(0,_("Loading Data..."))
            self.dictFile.load()
            data = self.dictFile.data
            self.data = data.get('installers',{})
            self.data_sizeCrcDate = data.get('sizeCrcDate',{})
            self.updateDictFile()
            self.loaded = True
            changed = True
        #--Last marker
        if self.lastKey not in self.data:
            self.data[self.lastKey] = InstallerMarker(self.lastKey)
        #--Refresh Other
        if 'D' in what: 
            changed |= Installer.refreshSizeCrcDate(
                dirs['mods'], self.data_sizeCrcDate, progress,
                settings['bash.installers.removeEmptyDirs'], fullRefresh)
        if 'I' in what: changed |= self.refreshRenamed()
        if 'I' in what: changed |= self.refreshInstallers(progress,fullRefresh)
        if 'O' in what or changed: changed |= self.refreshOrder()
        if 'N' in what or changed: changed |= self.refreshNorm()
        if 'S' in what or changed: changed |= self.refreshStatus()
        #--Done
        if changed: self.hasChanged = True
        return changed

    def updateDictFile(self):
        """Updates self.data to use new classes."""
        if self.dictFile.vdata.get('version',0): return
        #--Update to version 1
        for name in self.data.keys():
            installer = self.data[name]
            if isinstance(installer,Installer):
                self.data[name] = installer.__copy__(InstallerArchive)
        self.dictFile.vdata['version'] = 1

    def save(self):
        """Saves to pickle file."""
        if self.hasChanged:
            self.dictFile.data['installers'] = self.data
            self.dictFile.data['sizeCrcDate'] = self.data_sizeCrcDate
            self.dictFile.save()
            self.hasChanged = False

    #-# D.C.-G.
    def saveCfgFile(self):
        """Save the installers path to mash.ini."""
        mash_ini = False
        if GPath('mash.ini').exists():
            mashIni = ConfigParser.ConfigParser()
            mashIni.read('mash.ini')
            mash_ini = True
            instPath = GPath(mashIni.get('General','sInstallersDir').strip()).s
        else:
            instPath = ""
        if instPath != dirs["installers"].s:
            if not mash_ini:
                if os.path.exists(os.path.join(os.getcwd(), "mash_default.ini")):
                    f = open(os.path.join(os.getcwd(), "mash_default.ini"), "r")
                    d = f.read()
                    f.close()
                else:
                    d = "[General]\n"
                f = open(os.path.join(os.getcwd(), "mash.ini"), "w")
                f.write(d)
                f.close()
                mashIni = ConfigParser.ConfigParser()
                mashIni.read('mash.ini')
            mashIni.set("General","sInstallersDir",os.path.abspath(dirs["installers"].s))
            f = open(os.path.join(os.getcwd(), "mash.ini"),"w")
            mashIni.write(f)
            f.close()

    def getSorted(self,column,reverse):
        """Returns items sorted according to column and reverse."""
        data = self.data
        items = data.keys()
        if column == 'Package':
            items.sort(reverse=reverse)
        elif column == 'Files':
            items.sort(key=lambda x: len(data[x].fileSizeCrcs),reverse=reverse)
        else:
            items.sort()
            attr = column.lower()
            if column in ('Package','Group'):
                getter = lambda x: object.__getattribute__(data[x],attr).lower()
                items.sort(key=getter,reverse=reverse)
            else:
                getter = lambda x: object.__getattribute__(data[x],attr)
                items.sort(key=getter,reverse=reverse)
        #--Special sorters
        if settings['bash.installers.sortStructure']:
            items.sort(key=lambda x: data[x].type)
        if settings['bash.installers.sortActive']:
            items.sort(key=lambda x: not data[x].isActive)
        if settings['bash.installers.sortProjects']:
            items.sort(key=lambda x: not isinstance(data[x],InstallerProject))
        return items

    #--Item Info
    def getColumns(self,item=None):
        """Returns text labels for item or for row header if item == None."""
        columns = self.getParam('columns')
        if item == None: return columns[:]
        labels,installer = [],self.data[item]
        for column in columns:
            if column == 'Package': 
                labels.append(item.s)
            elif column == 'Files':
                labels.append(formatInteger(len(installer.fileSizeCrcs)))
            else:
                value = object.__getattribute__(installer,column.lower())
                if column in ('Package','Group'):
                    pass
                elif column == 'Order':
                    value = `value`
                elif column == 'Modified':
                    value = formatDate(value)
                elif column == 'Size':
                    value = formatInteger(value/1024)+' KB'
                else:
                    raise ArgumentError(column)
                labels.append(value)
        return labels

    def getGuiKeys(self,item):
        """Returns keys for icon and text and background colors."""
        installer = self.data[item]
        #--Text
        if installer.type == 2 and len(installer.subNames) == 2: 
            textKey = self.type_textKey[1]
        else:
            textKey = self.type_textKey.get(installer.type,'GREY')
        #--Background
        backKey = (installer.skipDirFiles and 'bash.installers.skipped') or None
        if installer.dirty_sizeCrc: 
            backKey = 'bash.installers.dirty'
        elif installer.underrides: 
            backKey = 'bash.installers.outOfOrder'
        #--Icon
        iconKey = ('off','on')[installer.isActive]+'.'+self.status_color[installer.status]
        if installer.type < 0: 
            iconKey = 'corrupt'
        elif isinstance(installer,InstallerProject): 
            iconKey += '.dir'
        return (iconKey,textKey,backKey)

    def getName(self,item): 
        """Returns a string name of item for use in dialogs, etc."""
        return item.s

    def getColumn(self,item,column):
        """Returns item data as a dictionary."""
        raise UncodedError

    def setColumn(self,item,column,value):
        """Sets item values from a dictionary."""
        raise UncodedError

    #--Dict Functions -----------------------------------------------------------
    def __delitem__(self,item):
        """Delete an installer. Delete entry AND archive file itself."""
        if item == self.lastKey: return
        installer = self.data[item]
        apath = self.dir.join(item)
        if isinstance(installer,InstallerProject):
            apath.rmtree(safety='Installers')
        else:
            apath.remove()
        del self.data[item]

    def copy(self,item,destName,destDir=None):
        """Copies archive to new location."""
        if item == self.lastKey: return
        destDir = destDir or self.dir
        apath = self.dir.join(item)
        apath.copyTo(destDir.join(destName))
        if destDir == self.dir:
            self.data[destName] = installer = copy.copy(self.data[item])
            installer.isActive = False
            self.refreshOrder()
            self.moveArchives([destName],self.data[item].order+1)

    #--Refresh Functions --------------------------------------------------------
    def refreshRenamed(self):
        """Refreshes Installer.off_local from corresponding csv file."""
        changed = False
        pRenamed = dirs['mods'].join('Mash','Official_Local.csv')
        if not pRenamed.exists():
            changed = bool(Installer.off_local)
            self.renamedSizeDate = (0,0)
            Installer.off_local.clear()
        elif self.renamedSizeDate != (pRenamed.size,pRenamed.mtime):
            self.renamedSizeDate = (pRenamed.size,pRenamed.mtime)
            off_local = {}
            reader = bolt.CsvReader(pRenamed)
            for fields in reader:
                if len(fields) < 2 or not fields[0] or not fields[1]: continue
                off,local = map(string.strip,fields[:2])
                if not reModExt.search(off) or not reModExt.search(local): continue
                off,local = map(GPath,(off,local))
                if off != local: off_local[off] = local
            reader.close()
            changed = (off_local != Installer.off_local)
            Installer.off_local = off_local
        #--Refresh Installer mappings
        if changed:
            for installer in self.data.itervalues():
                installer.refreshDataSizeCrc()
        #--Done
        return changed

    def refreshInstallers(self,progress=None,fullRefresh=False):
        """Refresh installer data."""
        progress = progress or bolt.Progress()
        changed = False
        pending = set()
        projects = set()
        #--Current archives
        newData = {}
        for i in self.data.keys():
            if isinstance(self.data[i],InstallerMarker):
                newData[i] = self.data[i]
        #newData[self.lastKey] = self.data[self.lastKey]
        for archive in dirs['installers'].list():
            apath = dirs['installers'].join(archive)
            isdir = apath.isdir()
            if isdir: projects.add(archive)
            if (isdir and archive != 'Bash') or archive.cext in ('.7z','.zip','.rar'):
                installer = self.data.get(archive)
                if not installer:
                    pending.add(archive)
                elif (isdir and not installer.refreshed) or (
                    (installer.size,installer.modified) != (apath.size,apath.mtime)):
                    newData[archive] = installer
                    pending.add(archive)
                else:
                    newData[archive] = installer
        if fullRefresh: pending |= set(newData)
        changed = bool(pending) or (len(newData) != len(self.data))
        #--New/update crcs?
        for subPending,iClass in zip(
            (pending - projects, pending & projects),
            (InstallerArchive, InstallerProject)
            ):
            if not subPending: continue
            progress(0,_("Scanning Packages..."))
            progress.setFull(len(subPending))
            for index,package in enumerate(sorted(subPending)):
                progress(index,_("Scanning Packages...\n")+package.s)
                installer = newData.get(package)
                if not installer:
                    installer = newData.setdefault(package,iClass(package))
                apath = dirs['installers'].join(package)
                try: installer.refreshBasic(apath,SubProgress(progress,index,index+1))
                except InstallerArchiveError:
                    installer.type = -1
        self.data = newData
        return changed

    def refreshRenamedNeeded(self):
        pRenamed = dirs['mods'].join('Mash','Official_Local.csv')
        if not pRenamed.exists(): return bool(Installer.off_local)
        else: return (self.renamedSizeDate != (pRenamed.size,pRenamed.mtime))

    def refreshInstallersNeeded(self):
        """Returns true if refreshInstallers is necessary. (Point is to skip use 
        of progress dialog when possible."""
        for archive in dirs['installers'].list():
            apath = dirs['installers'].join(archive)
            if not apath.isfile() or not archive.cext in ('.7z','.zip','.rar'):
                continue
            installer = self.data.get(archive)
            if not installer or (installer.size,installer.modified) != (apath.size,apath.mtime):
                return True
        return False

    def refreshOrder(self):
        """Refresh installer status."""
        changed = False
        data = self.data
        ordered,pending = [],[]
        for archive,installer in self.data.iteritems():
            if installer.order >= 0:
                ordered.append(archive)
            else:
                pending.append(archive)
        pending.sort()
        ordered.sort()
        ordered.sort(key=lambda x: data[x].order)
        if self.lastKey in ordered:
            index = ordered.index(self.lastKey)
            ordered[index:index] = pending
        else:
            ordered += pending
        order = 0
        for archive in ordered:
            if data[archive].order != order:
                data[archive].order = order
                changed = True
            order += 1
        return changed

    def refreshNorm(self):
        """Refresh self.abnorm_sizeCrc."""
        data = self.data
        active = [x for x in data if data[x].isActive]
        active.sort(key=lambda x: data[x].order)
        #--norm
        norm_sizeCrc = {}
        for package in active:
            norm_sizeCrc.update(data[package].data_sizeCrc)
        #--Abnorm
        abnorm_sizeCrc = {}
        data_sizeCrcDate = self.data_sizeCrcDate
        for path,sizeCrc in norm_sizeCrc.iteritems():
            sizeCrcDate = data_sizeCrcDate.get(path)
            if sizeCrcDate and sizeCrc != sizeCrcDate[:2]:
                abnorm_sizeCrc[path] = sizeCrcDate[:2]
        (self.abnorm_sizeCrc,oldAbnorm_sizeCrc) = (abnorm_sizeCrc,self.abnorm_sizeCrc)
        return abnorm_sizeCrc != oldAbnorm_sizeCrc

    def refreshStatus(self):
        """Refresh installer status."""
        changed = False
        for installer in self.data.itervalues():
            changed |= installer.refreshStatus(self)
        return changed

    #--Operations -------------------------------------------------------------
    def moveArchives(self,moveList,newPos):
        """Move specified archives to specified position."""
        moveSet = set(moveList)
        data = self.data
        numItems = len(data)
        orderKey = lambda x: data[x].order
        oldList = sorted(data,key=orderKey)
        newList = [x for x in oldList if x not in moveSet]
        moveList.sort(key=orderKey)
        newList[newPos:newPos] = moveList
        for index,archive in enumerate(newList):
            data[archive].order = index
        self.setChanged()

    def install(self,archives,progress=None,last=False,override=True):
        """Install selected archives.
        what: 
            'MISSING': only missing files.
            Otherwise: all (unmasked) files.
        """
        progress = progress or bolt.Progress()
        #--Mask and/or reorder to last
        mask = set()
        if last:
            self.moveArchives(archives,len(self.data))
        else:
            maxOrder = max(self[x].order for x in archives)
            for installer in self.data.itervalues():
                if installer.order > maxOrder and installer.isActive:
                    mask |= set(installer.data_sizeCrc)
        #--Install archives in turn
        progress.setFull(len(archives))
        archives.sort(key=lambda x: self[x].order,reverse=True)
        for index,archive in enumerate(archives):
            progress(index,archive.s)
            installer = self[archive]
            destFiles = set(installer.data_sizeCrc) - mask
            if not override:
                destFiles &= installer.missingFiles
            if destFiles:
                installer.install(archive,destFiles,self.data_sizeCrcDate,SubProgress(progress,index,index+1))
            installer.isActive = True
            mask |= set(installer.data_sizeCrc)
        self.refreshStatus()

    def uninstall(self,unArchives,progress=None):
        """Uninstall selected archives."""
        unArchives = set(unArchives)
        data = self.data
        data_sizeCrcDate = self.data_sizeCrcDate
        getArchiveOrder =  lambda x: self[x].order
        #--Determine files to remove and files to restore. Keep in mind that
        #  that multipe input archives may be interspersed with other archives
        #  that may block (mask) them from deleting files and/or may provide
        #  files that should be restored to make up for previous files. However,
        #  restore can be skipped, if existing files matches the file being 
        #  removed.
        masked = set()
        removes = set()
        restores = {}
        #--March through archives in reverse order...
        for archive in sorted(data,key=getArchiveOrder,reverse=True):
            installer = data[archive]
            #--Uninstall archive?
            if archive in unArchives:
                for data_sizeCrc in (installer.data_sizeCrc,installer.dirty_sizeCrc):
                    for file,sizeCrc in data_sizeCrc.iteritems():
                        sizeCrcDate = data_sizeCrcDate.get(file)
                        if file not in masked and sizeCrcDate and sizeCrcDate[:2] == sizeCrc:
                            removes.add(file)
            #--Other active archive. May undo previous removes, or provide a restore file.
            #  And/or may block later uninstalls.
            elif installer.isActive:
                files = set(installer.data_sizeCrc)
                myRestores = (removes & files) - set(restores)
                for file in myRestores:
                    if installer.data_sizeCrc[file] != data_sizeCrcDate.get(file,(0,0,0))[:2]:
                        restores[file] = archive
                    removes.discard(file)
                masked |= files
        #--Remove files
        emptyDirs = set()
        modsDir = dirs['mods']
        for file in removes:
            path = modsDir.join(file)
            path.remove()
            (path+'.ghost').remove()
            del data_sizeCrcDate[file]
            emptyDirs.add(path.head)
        #--Remove empties
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()
        #--De-activate
        for archive in unArchives: 
            data[archive].isActive = False
        #--Restore files
        restoreArchives = sorted(set(restores.itervalues()),key=getArchiveOrder,reverse=True)
        if ['bash.installers.autoAnneal'] and restoreArchives: 
            progress.setFull(len(restoreArchives))
            for index,archive in enumerate(restoreArchives):
                progress(index,archive.s)
                installer = data[archive]
                destFiles = set(x for x,y in restores.iteritems() if y == archive)
                if destFiles:
                    installer.install(archive,destFiles,data_sizeCrcDate,
                        SubProgress(progress,index,index+1))
        #--Done
        self.refreshStatus()

    def anneal(self,anPackages=None,progress=None):
        """Anneal selected packages. If no packages are selected, anneal all.
        Anneal will:
        * Correct underrides in anPackages.
        * Install missing files from active anPackages."""
        data = self.data
        data_sizeCrcDate = self.data_sizeCrcDate
        anPackages = set(anPackages or data)
        getArchiveOrder =  lambda x: data[x].order
        #--Get remove/refresh files from anPackages
        removes = set()
        for package in anPackages:
            installer = data[package]
            removes |= installer.underrides
            if installer.isActive:
                removes |= installer.missingFiles
                removes |= set(installer.dirty_sizeCrc)
        #--March through packages in reverse order...
        restores = {}
        for package in sorted(data,key=getArchiveOrder,reverse=True):
            installer = data[package]
            #--Other active package. May provide a restore file.
            #  And/or may block later uninstalls.
            if installer.isActive:
                files = set(installer.data_sizeCrc)
                myRestores = (removes & files) - set(restores)
                for file in myRestores:
                    if installer.data_sizeCrc[file] != data_sizeCrcDate.get(file,(0,0,0))[:2]:
                        restores[file] = package
                    removes.discard(file)
        #--Remove files
        emptyDirs = set()
        modsDir = dirs['mods']
        for file in removes:
            path = modsDir.join(file)
            path.remove()
            (path+'.ghost').remove()
            data_sizeCrcDate.pop(file,None)
            emptyDirs.add(path.head)
        #--Remove empties
        for emptyDir in emptyDirs:
            if emptyDir.isdir() and not emptyDir.list():
                emptyDir.removedirs()
        #--Restore files
        restoreArchives = sorted(set(restores.itervalues()),key=getArchiveOrder,reverse=True)
        if restoreArchives: 
            progress.setFull(len(restoreArchives))
            for index,package in enumerate(restoreArchives):
                progress(index,package.s)
                installer = data[package]
                destFiles = set(x for x,y in restores.iteritems() if y == package)
                if destFiles:
                    installer.install(package,destFiles,data_sizeCrcDate,
                        SubProgress(progress,index,index+1))

    def getConflictReport(self,srcInstaller,mode):
        """Returns report of overrides for specified package for display on conflicts tab.
        mode: O: Overrides; U: Underrides"""
        data = self.data
        srcOrder = srcInstaller.order
        conflictsMode = (mode == 'OVER')
        if conflictsMode:
            #mismatched = srcInstaller.mismatchedFiles | srcInstaller.missingFiles
            mismatched = set(srcInstaller.data_sizeCrc)
        else:
            mismatched = srcInstaller.underrides
        showInactive = conflictsMode and settings['bash.installers.conflictsReport.showInactive']
        showLower = conflictsMode and settings['bash.installers.conflictsReport.showLower']
        if not mismatched: return ''
        src_sizeCrc = srcInstaller.data_sizeCrc
        packConflicts = []
        getArchiveOrder =  lambda x: data[x].order
        for package in sorted(self.data,key=getArchiveOrder):
            installer = data[package]
            if installer.order == srcOrder: continue
            if not showInactive and not installer.isActive: continue
            if not showLower and installer.order < srcOrder: continue
            curConflicts = Installer.sortFiles([x.s for x,y in installer.data_sizeCrc.iteritems() 
                if x in mismatched and y != src_sizeCrc[x]])
            if curConflicts: packConflicts.append((installer.order,package.s,curConflicts))
        #--Unknowns
        isHigher = -1
        buff = cStringIO.StringIO()
        for order,package,files in packConflicts:
            if showLower and (order > srcOrder) != isHigher:
                isHigher = (order > srcOrder)
                buff.write('= %s %s\n' % ((_('Lower'),_('Higher'))[isHigher],'='*40))
            buff.write('==%d== %s\n'% (order,package))
            for file in files:
                buff.write(file)
                buff.write('\n')
            buff.write('\n')
        report = buff.getvalue()
        if not conflictsMode and not report and not srcInstaller.isActive:
            report = _("No Underrides. Mod is not completely un-installed.")
        return report

# Data Extensions ------------------------------------------------------------
#------------------------------------------------------------------------------
class RefReplacer:
    """Used by FileRefs to replace references."""
    def __init__(self,filePath=None):
        """Initialize."""
        self.srcModName = None #--Name of mod to import records from.
        self.srcDepends = {} #--Source mod object dependencies.
        self.newIds = {} #--newIds[oldId] = (newId1,newId2...)
        self.newIndex = {} #--newIndex[oldId] = Index of next newIds[oldId]
        self.usedIds = set() #--Records to import
        if filePath: self.loadText(filePath)

    def loadText(self,filePath):
        """Loads replacer information from file."""
        ins = file(filePath,'r')
        reComment = re.compile(r"#.*")
        reSection = re.compile(r'@ +(srcmod|replace)',re.M)
        reReplace = re.compile(r"(\w[-\w ']+)\s*:\s*(.+)")
        reNewIds  = re.compile(r",\s*")
        mode = None
        for line in ins:
            line = reComment.sub('',line.strip())
            maSection = reSection.match(line)
            if maSection:
                mode = maSection.group(1)
            elif not line: #--Empty/comment line
                pass
            elif mode == 'srcmod':
                self.srcModName = line
            elif mode == 'replace':
                maReplace = reReplace.match(line)
                if not maReplace: continue
                oldId = maReplace.group(1)
                self.newIds[oldId.lower()] = reNewIds.split(maReplace.group(2))
        ins.close()

    def getNewId(self,oldId):
        """Returns newId replacement for old id."""
        oldId = oldId.lower()
        newIds = self.newIds[oldId]
        if len(newIds) == 1:
            newId = newIds[0]
        else:
            index = self.newIndex.get(oldId,0)
            self.newIndex[oldId] = (index + 1) % len(newIds)
            newId = newIds[index]
        self.usedIds.add(newId.lower())
        return newId

    def getSrcRecords(self):
        """Returns list of records to insert into mod."""
        srcRecords = {}
        if self.srcModName and self.usedIds: 
            #--Get FileRep
            srcInfo = modInfos[self.srcModName]
            fullRep = srcInfo.extras.get('FullRep')
            if not fullRep:
                fullRep = FileRep(srcInfo)
                fullRep.load()
                srcInfo.extras['FullRep'] = fullRep
            for record in fullRep.records:
                id = record.getId().lower()
                if id in self.usedIds:
                    srcRecords[id] = copy.copy(record)
        return srcRecords

    def clearUsage(self):
        """Clears usage state."""
        self.newIndex.clear()
        del self.usedIds[:]

#------------------------------------------------------------------------------
class FileRep:
    """Abstract TES3 file representation."""
    def __init__(self, fileInfo,canSave=True,log=None,progress=None):
        """Initialize."""
        self.progress = progress or Progress()
        self.log = log or Log()
        self.fileInfo = fileInfo
        self.canSave = canSave
        self.tes3 = None
        self.records = []
        self.indexed = {} #--record = indexed[type][id]

    def load(self,keepTypes='ALL',factory={}):
        """Load file. If keepTypes, then only keep records of type in keepTypes or factory.
        factory: dictionary mapping record type to record class. For record types 
        in factory, specified class will be used and data will be kept."""
        keepAll = (keepTypes == 'ALL')
        keepTypes = keepTypes or set() #--Turns None or 0 into an empty set.
        #--Header
        inPath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        ins = Tes3Reader(self.fileInfo.name,file(inPath,'rb'))
        (name,size,delFlag,recFlag) = ins.unpackRecHeader()
        self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        #--Raw data read
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            if name in factory:
                record = factory[name](name,size,delFlag,recFlag,ins)
                self.records.append(record)
            elif keepAll or name in keepTypes:
                record = Record(name,size,delFlag,recFlag,ins)
                self.records.append(record)
            else:
                ins.seek(size,1,name)
        #--Done Reading
        ins.close()

    def unpackRecords(self,unpackTypes):
        """Unpacks records of specified types"""
        for record in self.records:
            if record.name in unpackTypes:
                record.load(unpack=True)

    def indexRecords(self,indexTypes):
        """Indexes records of specified types."""
        indexed = self.indexed = {}
        for type in indexTypes:
            indexed[type] = {}
        for record in self.records:
            type = record.name
            if type in indexTypes:
                indexed[type][record.getId().lower()] = record

    def loadUI(self,factory={}):
        """Convenience function. Loads, then unpacks, then indexes."""
        keepTypes = self.canSave and 'ALL' or tuple()
        self.load(keepTypes=keepTypes,factory=factory)
        uiTypes = set(factory.keys())
        self.unpackRecords(uiTypes)
        self.indexRecords(uiTypes)

    def getRecord(self,type,id,Class=None):
        """Gets record with corresponding type and id.
        If record doesn't exist and Class is provided, then a new instance 
        with given id is created, added to record list and indexed and then 
        returned to the caller."""
        idLower = id.lower()
        typeIds = self.indexed[type]
        if idLower in typeIds:
            return typeIds[idLower]
        elif Class:
            record = Class()
            record.id = id
            self.records.append(record)
            typeIds[idLower] = record
            return record
        else:
            return None

    def setRecord(self,record):
        """Adds record to record list and indexed."""
        idLower = record.getId().lower()
        type = record.name
        typeIds = self.indexed[type]
        if idLower in typeIds:
            oldRecord = typeIds[idLower]
            index = self.records.index(oldRecord)
            self.records[index] = record
        else:
            self.records.append(record)
        typeIds[idLower] = record

    def safeSave(self):
        """Save data to file safely."""
        self.fileInfo.makeBackup()
        filePath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        tempPath = filePath+'.tmp'
        self.save(tempPath)
        renameFile(tempPath,filePath)
        self.fileInfo.setMTime()
        self.fileInfo.extras.clear()

    def save(self,outPath=None):
        """Save data to file. 
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.canSave): raise StateError(_("Insufficient data to write file."))
        if not outPath:
            fileInfo = self.fileInfo
            outPath = os.path.join(fileInfo.dir,fileInfo.name)
        out = file(outPath,'wb')
        #--Tes3 Record
        self.tes3.setChanged()
        self.tes3.hedr.setChanged()
        self.tes3.hedr.numRecords = len(self.records) #--numRecords AFTER TES3 record
        self.tes3.getSize()
        self.tes3.dump(out)
        #--Other Records
        for record in self.records:
            record.getSize()
            record.dump(out)
        out.close()

    def sortRecords(self):
        #--Get record type order.
        import mush
        order = 0
        typeOrder = {}
        for typeIncrement in listFromLines(mush.recordTypes):
            (type,increment) = typeIncrement.split()
            if increment == '+': order += 1
            typeOrder[type] = order
        #--Get ids for records. (For subsorting.)
        ids = {}
        noSubSort = set(['CELL','LAND','PGRD','DIAL','INFO'])
        for record in self.records:
            recData = record.data
            if record.name in noSubSort:
                ids[record] = 0
            else:
                id = record.getId()
                ids[record] = id and id.lower()
        #--Sort
        self.records.sort(cmp=lambda a,b: 
            cmp(typeOrder[a.name],typeOrder[b.name]) or cmp(ids[a],ids[b]))

#------------------------------------------------------------------------------
class FileRefs(FileRep):
    """TES3 file representation with primary focus on references, but also 
    including other information used in file repair."""

    def __init__(self, fileInfo, skipNonCells=False, skipObjRecords=False,log=None,progress=None):
        canSave = not skipNonCells #~~Need to convert skipNonCells argument to this.
        FileRep.__init__(self, fileInfo, canSave,log,progress)
        self.skipObjRecords = skipObjRecords
        self.tes3 = None
        self.fmap = None
        self.records = []
        self.cells = []
        self.lands = {} #--Landscapes indexed by Land.id.
        #--Save Debris Info
        self.debrisIds = {}
        #--Content records
        self.conts = [] #--Content records: CREC, CNTC, NPCC
        self.conts_id = {}
        self.cells_id = {}
        self.refs_scpt = {} 
        self.scptRefs = set()
        self.isLoaded = False
        self.isDamaged = False

    #--File Handling---------------------------------------
    def setDebrisIds(self):
        """Setup to record ids to be used by WorldRefs.removeSaveDebris.
        Should be called before load or refresh."""
        for type in ['BOOK','CREA','GLOB','NPC_','LEVI','LEVC','FACT']:
            if type not in self.debrisIds:
                self.debrisIds[type] = []
        #--Built-In Globals (automatically added by game engine)
        for builtInGlobal in ('monthstorespawn','dayspassed'):
            if builtInGlobal not in self.debrisIds['GLOB']:
                self.debrisIds['GLOB'].append(builtInGlobal)

    def refreshSize(self):
        """Return file size if needs to be updated. Else return 0."""
        if self.isLoaded:
            return 0
        else:
            return self.fileInfo.size

    def refresh(self):
        """Load data if file has changed since last load."""
        if self.isDamaged:
            raise StateError(self.fileInfo.name+_(': Attempted to access damaged file.'))
        if not self.isLoaded:
            try:
                self.load()
                self.isLoaded = True
            except Tes3ReadError, error:
                self.isDamaged = True
                if not error.inName:
                    error.inName = self.fileInfo.name
                raise

    def load(self):
        """Load reference data from file."""
        #print self.fileInfo.name
        progress = self.progress
        filePath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        self.fileSize = os.path.getsize(filePath)
        #--Localize
        cells = self.cells
        records = self.records
        canSave = self.canSave
        skipObjRecords = self.skipObjRecords
        contTypes = set(['CREC','CNTC','NPCC'])
        levTypes = set(('LEVC','LEVI'))
        debrisIds = self.debrisIds
        debrisTypes = set(debrisIds.keys())
        #--Header
        inPath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        ins = Tes3Reader(self.fileInfo.name,file(inPath,'rb'))
        (name,size,delFlag,recFlag) = ins.unpackRecHeader()
        self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        if not canSave: del self.tes3.others[:]
        #--Progress info
        progress = self.progress
        progress(0.0,'Loading '+self.fileInfo.name)
        #--Raw data read
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            #print "%s [%d]" % (name,size)
            #--CELL?
            if name == 'CELL':
                record = Cell(name,size,delFlag,recFlag,ins,0,skipObjRecords)
                cells.append(record)
                if canSave: records.append(record)
            #--Contents
            elif canSave and name in contTypes:
                if name == 'CREC':
                    record = Crec(name,size,delFlag,recFlag,ins,True)
                elif name == 'CNTC':
                    record = Cntc(name,size,delFlag,recFlag,ins,True)
                else:
                    record = Npcc(name,size,delFlag,recFlag,ins,True)
                self.conts.append(record)
                self.conts_id[record.getId()] = record
                records.append(record)
            #--File Map
            elif name == 'FMAP':
                record = Fmap(name,size,delFlag,recFlag,ins)
                self.fmap = record
                records.append(record)
            #--Landscapes
            elif name == 'LAND':
                record = Land(name,size,delFlag,recFlag,ins)
                self.lands[record.getId()] = record
                records.append(record)
            #--Scripts
            elif canSave and name == 'SCPT':
                record = Scpt(name,size,delFlag,recFlag,ins,True)
                records.append(record)
                if record.getRef():
                    self.refs_scpt[record] = record.getRef()
            #--Save debris info?
            elif name in debrisTypes:
                record = Record(name,size,delFlag,recFlag,ins)
                id = record.getId()
                if id:
                    debrisIds[name].append(id.lower())
                if canSave:
                    records.append(record)
            #--Skip Non-cell?
            elif not canSave:
                ins.seek(size,1,name)
            #--Keep non-cell?
            else:
                records.append(Record(name,size,delFlag,recFlag,ins))
        #--Done Reading
        ins.close()
        #--Analyze Cells
        cntCells = 0
        progress.setMax(len(self.cells))
        for cell in self.cells:
            cell.load(None,1)
            self.cells_id[cell.getId()] = cell
            if not canSave:
                cell.data = None #--Free some memory
            #--Progress
            cntCells += 1
            progress(cntCells)
        #--Scripts
        if self.refs_scpt:
            self.updateScptRefs()

    def save(self,outPath=None):
        """Save data to file. 
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.canSave or self.skipObjRecords): raise StateError(_("Insufficient data to write file."))
        if not outPath:
            fileInfo = self.fileInfo
            outPath = os.path.join(fileInfo.dir,fileInfo.name)
        out = file(outPath,'wb')
        #--Tes3 Record
        self.tes3.changed = 1
        self.tes3.hedr.changed = 1
        self.tes3.hedr.numRecords = len(self.records) #--numRecords AFTER TES3 record
        self.tes3.getSize()
        self.tes3.dump(out)
        #--Size Cell Records
        cntRecords = 0
        progress = self.progress
        progress.setMax(len(self.cells))
        progress(0.0,'Saving '+self.fileInfo.name)
        for record in self.cells:
            record.getSize()
            #--Progress
            cntRecords += 1
            progress(cntRecords)
        #--Other Records
        for record in self.records:
            record.getSize() #--Should already be done, but just in case.
            record.dump(out)
        out.close()

    #--Renumbering-------------------------------------------------------------
    def getFirstObjectIndex(self):
        """Returns first object index number. Assumes that references are in linear order."""
        if not self.fileInfo.isEsp(): raise StateError(_('FileRefs.renumberObjects is for esps only.'))
        for cell in self.cells:
            objects = cell.getObjects()
            for object in objects.list():
                if object[0] == 0:
                    return object[1]
        return 0

    def renumberObjects(self,first):
        """Offsets all local object index numbers by specified amount. FOR ESPS ONLY!
        Returns number of objects changed."""
        if not self.fileInfo.isEsp(): raise StateError(_('FileRefs.renumberObjects is for esps only.'))
        if first <= 0: raise ArgumentError(_('First index should be a positive integer'))
        log = self.log
        next = int(first)
        for cell in self.cells:
            objects = cell.getObjects()
            for object in objects.list():
                if object[0] == 0:
                    newObject = (0,next)+object[2:]
                    objects.replace(object,newObject)
                    next += 1
        return (next - first)

    #--Remapping---------------------------------------------------------------
    def remap(self,newMasters,modMap,objMaps=[]):
        """Remap masters and modIndexes.
        newMasters -- New master list. Same format as Cell.masters.
        modMap -- mapping dictionary so that newModIndex = modMap[oldModIndex]
        objMaps -- ObjectIndex mapping dictionaries"""
        #--Masters
        self.tes3.masters = newMasters
        #--File mapping
        modMapKeys = modMap.keys()
        #--Remap iObjs
        cells_id = self.cells_id
        reObjNum = re.compile('[0-9A-Z]{8}$')
        for (iMod,objMap) in objMaps:
            cellIds = objMap.keys()
            for cellId in cellIds:
                cellObjMap = objMap[cellId]
                #--Save 
                cell = cells_id.get(cellId)
                if not cell: continue
                #--Objects
                objects = cell.getObjects()
                for object in objects.list():
                    #--Different mod?
                    if object[0] != iMod:
                        pass
                    #--Cell deleted?
                    elif cellObjMap == -1:
                        objects.remove(object)
                    #--Remapped object?
                    elif object[1] in cellObjMap:
                        (newIObj,objId) = cellObjMap[object[1]]
                        objIdBase = reObjNum.sub('',objId) #--Strip '00001234' id num from object
                        #--Mismatched object id?
                        if objId != objIdBase:
                            #print 'Mismatch:',object[:3]
                            pass 
                        #--Deleted object?
                        elif newIObj == -1:
                            #print 'Deleted',object[:3]
                            objects.remove(object)
                        #--Remapped object?
                        else:
                            #print 'Remapped',object[:3],'to',newIObj
                            newObject = self.remapObject(object,iMod,newIObj)
                            objects.replace(object,newObject)
        self.updateScptRefs()
        #--Remap iMods
        if not modMapKeys: return
        for cell in self.cells:
            objects = cell.getObjects()
            for object in objects.list():
                #--Remap IMod
                iMod = object[0]
                #--No change?
                if iMod not in modMapKeys: 
                    pass
                #--Object deleted?
                elif modMap[iMod] == -1:
                    objects.remove(object)
                #--Object not deleted?
                else:
                    newObject = self.remapObject(object,modMap[iMod])
                    objects.replace(object,newObject)
        self.updateScptRefs()

    def remapObject(self,object,newIMod,newIObj=-1):
        """Returns an object mapped to a newMod."""
        (iMod,iObj,objId,objRecords) = object[:4]
        if newIObj == -1: newIObj = iObj
        newObject = (newIMod,newIObj)+object[2:]
        if objRecords and objRecords[0].name == 'MVRF':
            data = cStringIO.StringIO()
            data.write(struct.pack('i',newIObj)[:3])
            data.write(struct.pack('B',newIMod))
            objRecords[0].data = data.getvalue()
            objRecords[0].setChanged(False)
            data.close()
            #print 'Remapped MVRF:',newObject[:3]
        #--Remap any script references
        oldRef = (iMod,iObj)
        if oldRef in self.scptRefs:
            newRef = (newIMod,newIObj)
            for scpt in self.refs_scpt.keys():
                if self.refs_scpt[scpt] == oldRef:
                    scpt.setRef(newRef)
                    self.refs_scpt[scpt] = newRef
                    #print object[:3],newRef, scpt.id
                    #--Be sure to call updateScptRefs when finished remapping *all* objects.
        #--Done
        return newObject

    def updateScptRefs(self):
        """Updates refs_scpt and scptRefs data. Call after all objects have been remapped."""
        for scpt in self.refs_scpt.keys():
            self.refs_scpt[scpt] = scpt.getRef()
        self.scptRefs = set(self.refs_scpt.values())

    def listBadRefScripts(self):
        """Logs any scripts with bad refs."""
        if not self.log: return
        ids = []
        for record in self.records:
            if record.name != 'SCPT': continue
            rnam = record.rnam
            if rnam and rnam.data == chr(255)*4:
                ids.append(record.getId())
        if ids:
            self.log.setHeader(_('Detached Global Scripts'))
            for id in sorted(ids,key=string.lower):
                self.log(id)

    def getObjectMap(self,oldRefs):
        """Returns an iObj remapping from an old FileRefs to this FileRefs.
        
        This is used to update saved games from one version of a mod to a newer version."""
        objMap = {} #--objMap[cellId][oldIObj] = newIObj
        #--Old cells
        for oldCell in oldRefs.cells:
            cellId = oldCell.getId()
            newCell = self.cells_id.get(cellId)
            #--Cell deleted?
            if not newCell:
                objMap[cellId] = -1
                continue
            cellObjMap = {}
            newObjects = newCell.getObjects().list()
            nextObjectIndex = {}
            #--Old Objects
            for oldObject in oldCell.getObjects().list():
                (iMod,oldIObj,objId) = oldObject[:3]
                if iMod: continue #--Skip mods to masters
                #--New Objects
                objIndex = nextObjectIndex.get(objId,0)
                newIObj = -1 #--Delete by default
                while objIndex < len(newObjects):
                    newObject = newObjects[objIndex]
                    objIndex += 1
                    if newObject[0]: continue #--Skip mods to masters
                    if newObject[2] == objId:
                        newIObj = newObject[1]
                        break
                nextObjectIndex[objId] = objIndex
                #--Obj map has changed?
                if newIObj != oldIObj:
                    cellObjMap[oldIObj] = (newIObj,objId)
            #--Save mapping for this cell?
            if cellObjMap: objMap[cellId] = cellObjMap
        #--Done
        return objMap
        
    #--Removers ---------------------------------------------------------------
    def removeLvcrs(self):
        """Remove all LVCR refs. 
        In save game, effect is to reset the spawn point."""
        count = 0
        for cell in self.cells:
            #print cell.getId()
            objects = cell.getObjects()
            for object in objects.list():
                for objRecord in object[3]:
                    if objRecord.name == 'LVCR':
                        #print ' ',object[:3]
                        objects.remove(object)
                        count += 1
                        break
        return count
                
    def removeOrphanContents(self):
        """Remove orphaned content records."""
        reObjNum = re.compile('[0-9A-Z]{8}$')
        #--Determine which contIds are matched to a reference.
        contIds = set(self.conts_id.keys())
        matched = dict([(id,False) for id in contIds])
        for cell in self.cells:
            objects = cell.getObjects()
            for object in objects.list():
                objId= object[2]
                #--LVCR? Get id of spawned creature instead.
                for objRecord in object[3]:
                    if objRecord.name == 'NAME':
                        objId = cstrip(objRecord.data)
                        break
                if reObjNum.search(objId):
                    if objId in contIds:
                        matched[objId] = True
        #--Special case: PlayerSaveGame
        matched['PlayerSaveGame00000000'] = True
        #--unmatched = container records that have not been matched.
        orphans = set([self.conts_id[id] for id in contIds if not matched[id]])
        for orphan in sorted(orphans, key=lambda a: a.getId().lower()):
            self.log('  '+orphan.getId())
        #--Delete Records
        self.records = [record for record in self.records if record not in orphans]
        self.conts   = [record for record in self.conts if record not in orphans]
        self.conts_id = dict([(id,record) for id,record in self.conts_id.iteritems() if matched[id] > 0])
        return len(orphans)

    def removeRefsById(self,objIds,safeCells=[]):
        """Remove refs with specified object ids, except in specified cells.
        objIds -- Set of object ids to re removed.
        skipCells -- Set of cell names to be skipped over."""
        reObjNum = re.compile('[0-9A-F]{8}$')
        delCount = {}
        reSafeCells = re.compile('('+('|'.join(safeCells))+')')
        cellsSkipped = []
        for cell in self.cells:
            #print cell.getId()
            if safeCells and reSafeCells.match(cell.getId()):
                cellsSkipped.append(cell.getId())
                continue
            objects = cell.getObjects()
            for object in objects.list():
                objId = object[2]
                #--If ref is a spawn point, then use id of spawned creature.
                for objRecord in object[3]:
                    if objRecord.name == 'NAME':
                        objId = cstrip(objRecord.data)
                        break
                objBase = reObjNum.sub('',objId) #--Strip '00001234' id num from object
                if objBase in objIds:
                    objects.remove(object)
                    delCount[objBase] = delCount.get(objBase,0) + 1
        #--Done
        log = self.log
        log.setHeader('Cells Skipped:')
        for cell in sorted(cellsSkipped,key=lambda a: a.lower()):
            log('  '+cell)
        log.setHeader('References Deleted:')
        for objId in sorted(delCount.keys(),key=lambda a: a.lower()):
            log('  %03d  %s' % (delCount[objId],objId))

    #--Replacers --------------------------------------------------------------
    def replaceRefsById(self,refReplacer):
        """Replace refs according to refReplacer."""
        log = self.log
        oldIds = set(refReplacer.newIds.keys())
        replCount = {}
        for cell in self.cells:
            objects = cell.getObjects()
            for object in objects.list():
                (iMod,iObj,oldId,objRecords) = object[:4]
                if oldId.lower() in oldIds:
                    newId = refReplacer.getNewId(oldId)
                    newObject = (iMod,iObj,newId,objRecords)
                    objects.replace(object,newObject)
                    replCount[oldId] = replCount.get(oldId,0) + 1
        #--Add Records?
        newRecords = refReplacer.getSrcRecords()
        if newRecords:
            selfIds = set([record.getId().lower() for record in self.records if record.getId()])
            log.setHeader(_('Records added:'))
            for newId in sorted(newRecords.keys()):
                if newId not in selfIds:
                    self.records.append(newRecords[newId])
                    log(newId)
        #--Log
        log.setHeader(_('References replaced:'))
        for oldId in sorted(replCount.keys(),key=lambda a: a.lower()):
            log('%03d %s' % (replCount[oldId], oldId))
        #--Return number of references replaced.
        return sum(replCount.values())

#------------------------------------------------------------------------------
class WorldRefs:
    """World references as defined by a set of masters (esms and esps)."""
    def __init__(self,masterNames = [], progress=None, log=None):
        self.progress = progress or Progress()
        self.log = log or Log()
        self.levListMasters = {} #--Count of masters for each leveled list (LEVC or LEVI)
        self.masterNames = [] #--Names of masters, in order added
        self.extCellNames = set() #--Named exterior cells.
        self.cellRefIds = {}  #--objId = cellRefIds[cellId][(iMod,iObj)]
        self.cellRefAlts = {} #--(iModNew,iObj) = cellRefAlts[cellId][(iModOld,iObj)]
        self.debrisIds = {}
        self.lands = {} #--Landscape records indexed by landscape record id.
        if masterNames:
            self.addMasters(masterNames)

    def addMasters(self,masterNames):
        """Add a list of mods."""
        #--Load Masters
        #--Master FileRefs
        proItems = []
        totSize = 0
        for masterName in masterNames:
            #--Don't have fileRef? FileRef out of date?
            masterInfo = modInfos[masterName]
            fileRefs = masterInfo.extras.get('FileRefs')
            if not fileRefs:
                fileRefs = masterInfo.extras['FileRefs'] = FileRefs(masterInfo,True,True)
                fileRefs.setDebrisIds()
            refreshSize = fileRefs.refreshSize()
            if refreshSize:
                proItems.append((fileRefs,refreshSize))
                totSize += refreshSize
        #--Refresh masters
        cumSize = 0
        for (fileRefs,size) in proItems:
            self.progress.setBaseScale(1.0*cumSize/totSize, 1.0*size/totSize)
            fileRefs.progress = self.progress
            fileRefs.refresh()
            cumSize += size
        #--Do Mapping
        del proItems[:]
        totSize = 0
        for masterName in masterNames:
            size = len(modInfos[masterName].extras['FileRefs'].cells)
            proItems.append((masterName,size))
            totSize += size
        cumSize = 0
        for (masterName,size) in proItems:
            if size: self.progress.setBaseScale(1.0*cumSize/totSize, 1.0*size/totSize)
            self.addMaster(masterName)
            cumSize += size

    def addMaster(self,masterName):
        """Add a single mod."""
        masterInfo = modInfos[masterName]
        self.masterNames.append(masterName)
        #--Map info
        iMod = len(self.masterNames)
        #--Map masters
        masterMap = self.getMasterMap(masterInfo)
        masterRefs = masterInfo.extras['FileRefs']
        #--Get Refs types and alts
        cellRefIds = self.cellRefIds
        cellRefAlts = self.cellRefAlts
        #--Progress
        cntCells = 0
        progress = self.progress
        progress.setMax(len(masterRefs.cells))
        progress(0.0,_("Building ")+masterName)
        for cell,record in masterRefs.lands.items():
            self.lands[cell] = record
        for masterCell in masterRefs.cells:
            cellId = masterCell.getId()
            #--Named exterior cell?
            if not (masterCell.flags & 1) and masterCell.cellName:
                self.extCellNames.add(masterCell.cellName)
            #--New cell id?
            if cellId not in cellRefIds:
                refIds = cellRefIds[cellId] = {}
                refAlts = cellRefAlts[cellId] = {}
            #--Exiting cell id?
            else:
                refIds = cellRefIds[cellId]
                refAlts = cellRefAlts[cellId]
            #--Objects
            for object in masterCell.getObjects().list():
                (iMMod,iObj,objId) = object[:3]
                newIdKey = (iMod,iObj)
                #--Modifies a master reference?
                if iMMod:
                    if iMMod >= len(masterMap):
                        raise Tes3RefError(masterName,cellId,objId,iObj,iMMod,
                            _('NO SUCH MASTER'))
                    altKey = (masterMap[iMMod],iObj)
                    oldIdKey = altKey
                    #--Already modified?
                    if altKey in refAlts:
                        oldIdKey = refAlts[altKey]
                    if oldIdKey not in refIds:
                        raise Tes3RefError(masterName,cellId,objId,iObj,iMMod,
                            masterInfo.masterNames[iMMod-1])
                    del refIds[oldIdKey]
                    refAlts[altKey] = newIdKey
                    #print cellId, newIdKey, objId
                #--Save it
                refIds[newIdKey] = objId
            #--Progress
            cntCells += 1
            progress(cntCells)
        #--Debris Ids
        for type, ids in masterRefs.debrisIds.items():
            if type not in self.debrisIds:
                self.debrisIds[type] = set()
            self.debrisIds[type].update(ids)
        #--List Masters
        levListMasters = self.levListMasters
        for levList in (masterRefs.debrisIds['LEVC'] + masterRefs.debrisIds['LEVI']):
            if levList not in levListMasters:
                levListMasters[levList] = []
            levListMasters[levList].append(masterName)

    def getMasterMap(self,masterInfo):
        """Return a map of a master's masters to the refworld's masters."""
        masterMap = [0]
        #--Map'em
        for mmName in masterInfo.masterNames:
            if mmName not in self.masterNames: 
                raise MoshError(_("Misordered esm: %s should load before %s") % (mmName, masterInfo.name))
            masterMap.append(self.masterNames.index(mmName)+1)
        #--Done
        return masterMap       
        
    #--Repair ---------------------------------------------
    def removeDebrisCells(self,fileRefs):
        """Removes debris cells -- cells that are not supported by any of the master files."""
        #--Make sure fileRefs for a save file!
        if not fileRefs.fileInfo.isEss():
            fileName = fileRefs.fileInfo.fileName
            raise ArgumentError(_('Cannot remove debris cells from a non-save game!')+fileName)
        log = self.log
        cntDebrisCells = 0
        log.setHeader("Debris Cells")
        for cell in fileRefs.cells:
            #--Cell Id
            cellId = cell.getId()
            if cellId not in self.cellRefIds:
                log(cellId)
                fileRefs.records.remove(cell)
                fileRefs.cells.remove(cell)
                del fileRefs.cells_id[cellId]
                cntDebrisCells += 1
        return cntDebrisCells

    def removeDebrisRecords(self,fileRefs):
        """Removes debris records (BOOK, CREA, GLOB, NPC_) that are not present 
        in masters and that aren't constructed in game (custom enchantment scrolls)."""
        #--Make sure fileRefs for a save file!
        if not fileRefs.fileInfo.isEss():
            fileName = fileRefs.fileInfo.fileName
            raise ArgumentError(_('Cannot remove save debris from a non-save game!')+fileName)
        goodRecords = []
        debrisIds = self.debrisIds
        debrisTypes = set(debrisIds.keys())
        reCustomId = re.compile('^\d{10,}$')
        removedIds = {}
        for record in fileRefs.records:
            type = record.name
            if type in debrisTypes:
                id = record.getId()
                if id and id.lower() not in debrisIds[type] and not reCustomId.match(id):
                    if type not in removedIds:
                        removedIds[type] = []
                    removedIds[type].append(id)
                    continue #--Skip appending this record to good records.
            goodRecords.append(record)
        #--Save altered record list?
        cntDebrisIds = 0
        if removedIds:
            #--Save changes
            del fileRefs.records[:]
            fileRefs.records.extend(goodRecords)
            #--Log
            log = self.log
            for type in sorted(removedIds.keys()):
                log.setHeader(_("Debris %s:") % (type,))
                for id in sorted(removedIds[type],key=lambda a: a.lower()):
                    log('  '+id)
                cntDebrisIds += len(removedIds[type])
        return cntDebrisIds

    def removeOverLists(self,fileRefs):
        """Removes leveled lists when more than one loaded mod changes that 
        same leveled list."""
        if not fileRefs.fileInfo.isEss():
            fileName = fileRefs.fileInfo.fileName
            raise ArgumentError(_('Cannot remove overriding lists from a non-save game!')+fileName)
        listTypes = set(('LEVC','LEVI'))
        levListMasters = self.levListMasters
        log = self.log
        cntLists = 0
        log.setHeader(_("Overriding Lists"))
        #--Go through records and trim overriding lists.
        goodRecords = []
        for record in fileRefs.records:
            type = record.name
            if type in listTypes:
                id = record.getId()
                idl = id.lower()
                masters = levListMasters.get(idl,'')
                if len(masters) != 1:
                    log('  '+id)
                    for master in masters:
                        log('    '+master)
                    cntLists += 1
                    #del fileRefs.debrisIds[type][idl]
                    continue #--Skip appending this record to good records.
            goodRecords.append(record)
        del fileRefs.records[:]
        fileRefs.records.extend(goodRecords)
        return cntLists

    def repair(self,fileRefs):
        """Repair the references for a file."""
        #--Progress/Logging
        log = self.log
        logBDD = _('BAD DELETE>>DELETED %d %d %s')
        logBRR = _('BAD REF>>REMATCHED  %d %d %s %d')
        logBRN = _('BAD REF>>NO MASTER  %d %d %s')
        logBRD = _('BAD REF>>DOUBLED    %d %d %s')
        #----
        isMod = (fileRefs.fileInfo.isMod())
        reObjNum = re.compile('[0-9A-Z]{8}$')
        emptyDict = {}
        cellRefIds = self.cellRefIds
        cntRepaired = 0
        cntDeleted = 0
        cntUnnamed = 0
        for cell in fileRefs.cells:
            #--Data arrays
            usedKeys = []
            badDeletes = []
            badObjects = []
            doubleObjects = []
            refMods = {}
            #--Cell Id
            cellId = cell.getId()
            log.setHeader(cellId)
            #--Debris cell name?
            if not isMod:
                cellName = cell.cellName
                if not (cell.flags & 1) and cellName and (cellName not in self.extCellNames):
                    log(_("Debris Cell Name: ")+cellName)
                    cell.flags &= ~32
                    cell.cellName = ''
                    cell.setChanged()
                    cntUnnamed += 1
            refIds = cellRefIds.get(cellId,emptyDict) #--Empty if cell is new in fileRefs.
            objects = cell.getObjects()
            for object in objects.list():
                (iMod,iObj,objId,objRecords) = object[:4]
                refKey = (iMod,iObj)
                #--Used Key?
                if refKey in usedKeys:
                    log(logBRD % object[:3])
                    objects.remove(object)
                    doubleObjects.append(object)
                    cell.setChanged()
                #--Local object?
                elif not iMod:
                    #--Object Record
                    for objRecord in objRecords:
                        #--Orphan delete?
                        if objRecord.name == 'DELE':
                            log(logBDD % object[:3])
                            objects.remove(object)
                            badDeletes.append(object)
                            cntDeleted += 1
                            cell.setChanged()
                            break
                    #--Not Deleted?
                    else: #--Executes if break not called in preceding for loop.
                        usedKeys.append(refKey)
                #--Modified object?
                else:
                    refId = refIds.get(refKey,None)
                    objIdBase = reObjNum.sub('',objId) #--Strip '00001234' id num from object
                    #--Good reference?
                    if refId and (isMod or (refId == objIdBase)):
                        usedKeys.append(refKey)
                    #--Missing reference?
                    else:
                        badObjects.append(object)
                        cell.setChanged()
            #--Fix bad objects.
            if badObjects:
                #--Build rematching database where iMod = refMods[(iObj,objId)]
                refMods = {}
                repeatedKeys = []
                for refId in refIds.keys():
                    (iMod,iObj) = refId
                    objId = refIds[refId]
                    key = (iObj,objId)
                    #--Repeated Keys?
                    if key in refMods: 
                        repeatedKeys.append(key)
                    else:
                        refMods[key] = iMod
                #--Remove remaps for any repeated keys
                for key in repeatedKeys:
                    if key in refMods: del refMods[key]
                #--Try to remap
                for object in badObjects:
                    (iMod,iObj,objId) = object[:3]
                    objIdBase = reObjNum.sub('',objId) #--Strip '00001234' id num from object
                    refModsKey = (iObj,objIdBase)
                    newMod = refMods.get(refModsKey,None)
                    #--Valid rematch?
                    if newMod and ((newMod,iObj) not in usedKeys):
                        log(logBRR % (iMod,iObj,objId,newMod))
                        usedKeys.append((newMod,iObj))
                        objects.replace(object,fileRefs.remapObject(object,newMod))
                        cntRepaired += 1
                    elif not newMod:
                        log(logBRN % tuple(object[:3]))
                        objects.remove(object)
                        cntDeleted += 1
                    else:
                        log(logBRD % tuple(object[:3]))
                        objects.remove(object)
                        cntDeleted += 1
        #--Done
        fileRefs.updateScptRefs()
        return (cntRepaired,cntDeleted,cntUnnamed)

    def repairWorldMap(self,fileRefs,gridLines=True):
        """Repair savegame's world map."""
        if not fileRefs.fmap: return 0
        progress = self.progress
        progress.setMax((28*2)**2)
        progress(0.0,_("Drawing Cells"))
        proCount = 0
        for gridx in range(-28,28,1):
            for gridy in range(28,-28,-1):
                id = '[%d,%d]' % (gridx,gridy)
                cell = fileRefs.cells_id.get(id,None)
                isMarked = cell and cell.flags & 32
                fileRefs.fmap.drawCell(self.lands.get(id),gridx,gridy,isMarked)
                proCount += 1
                progress(proCount)
        fileRefs.fmap.drawGrid(gridLines)
        return 1

#------------------------------------------------------------------------------
class FileDials(FileRep):
    """TES3 file representation focussing on dialog.

    Only TES3 DIAL and INFO records are analyzed. All others are left in raw data 
    form. """
    def __init__(self, fileInfo, canSave=True):
        FileRep.__init__(self,fileInfo,canSave)
        self.dials = []
        self.infos = {} #--info = self.infos[(dial.type,dial.id,info.id)]

    def load(self,factory={}):
        """Load dialogs from file."""
        canSave = self.canSave
        InfoClass = factory.get('INFO',InfoS) #--Info class from factory.
        #--Header
        inPath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        ins = Tes3Reader(self.fileInfo.name,file(inPath,'rb'))
        (name,size,delFlag,recFlag) = ins.unpackRecHeader()
        self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        #--Raw data read
        dial = None
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            #--DIAL?
            if name == 'DIAL':
                dial = Dial(name,size,delFlag,recFlag,ins,True)
                self.dials.append(dial)
                if canSave: self.records.append(dial)
            #--INFO?
            elif name == 'INFO':
                info = InfoClass(name,size,delFlag,recFlag,ins,True)
                self.records.append(info)
                dial.infos.append(info)
                self.infos[(dial.type,dial.id,info.id)] = info
            #--Non-dials?
            elif canSave:
                record = Record(name,size,delFlag,recFlag,ins)
                self.records.append(record)
            else:
                ins.seek(size,1,'Record')
        #--Done Reading
        ins.close()

    def save(self,outPath=None):
        """Save data to file. 
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.canSave): raise StateError(_("Insufficient data to write file."))
        FileRep.save(self,outPath)

    def loadText(self,textFileName):
        """Replaces dialog text with text read from file."""
        #--Text File
        infoKey = None
        text = None
        texts = {}
        reHeader = re.compile('^#')
        reInfo = re.compile('@ +(\d) +"(.+?)" +(\d+)')
        reSingleQuote = re.compile('[\x91\x92]')
        reDoubleQuote = re.compile('[\x93\x94]')
        reEllipsis = re.compile('\x85')
        reEolSpaces = re.compile(r' +\r\n')
        reExtraSpaces = re.compile(r'  +')
        reIllegalChars = re.compile(r'[@#]')
        #--Read file
        textFile = file(textFileName,'rb')
        for line in textFile:
            if reHeader.match(line): continue
            maInfo = reInfo.match(line)
            if maInfo:
                infoKey = (int(maInfo.group(1)),maInfo.group(2),maInfo.group(3))
                texts[infoKey] = text = []
            else:
                text.append(line)
        textFile.close()
        #--Strip and clean texts
        updated = []
        unmatched = []
        trimmed = {}
        for infoKey in texts.keys():
            if infoKey not in self.infos:
                unmatched.append(infoKey)
                continue
            text = ''.join(texts[infoKey])
            #--Required Subs
            text = text.strip(' \r\n')
            text = reSingleQuote.sub('\'',text)
            text = reDoubleQuote.sub('"',text)
            text = reEllipsis.sub('...',text)
            text = reIllegalChars.sub('',text)
            #--Optional subs
            text = reEolSpaces.sub('\r\n',text)
            text = reExtraSpaces.sub(' ',text)
            #--Trim?
            if len(text) > 511:
                trimmed[infoKey] = (text[:511],text[511:])
                text = text[:511]
            info = self.infos[infoKey]
            if text != info.text:
                info.text = text
                info.setChanged()
                updated.append(infoKey)
        #--Report
        buff = cStringIO.StringIO()
        for header,infoKeys in ((_('Updated'),updated),(_('Unmatched'),unmatched)):
            if infoKeys:
                buff.write('=== %s\n' % (header,))
            for infoKey in infoKeys:
                buff.write('* %s\n' % (infoKey,))
        if trimmed:
            buff.write('=== %s\n' % (_('Trimmed'),))
            for infoKey,(preTrim,postTrim) in trimmed.items():
                buff.write(`infoKey`+'\n'+preTrim+'<<<'+postTrim+'\n\n')
        return buff.getvalue()

    def dumpText(self,textFileName,groupBy='spId',spId=None):
        """Dumps dialogs to file."""
        newDials = self.dials[:]
        newDials.sort(key=lambda a: a.id.lower())
        newDials.sort(key=lambda a: a.type,reverse=True)
        infoKeys = []
        for dial in newDials:
            dial.sortInfos()
            for info in dial.infos:
                infoKeys.append((dial.type,dial.id,info.id))
        if groupBy == 'spId':
            infoKeys.sort(key=lambda a: self.infos[a].spId and self.infos[a].spId.lower())
        #--Text File
        textFile = file(textFileName,'wb')
        prevSpId = prevTopic = -1
        for infoKey in infoKeys:
            info = self.infos[infoKey]
            #--Filter by spId?
            if spId and info.spId != spId: continue
            #--Empty text?
            if not info.text: continue
            #--NPC Header?
            if groupBy == 'spId' and info.spId != prevSpId:
                prevSpId = info.spId
                header = prevSpId or ''
                textFile.write('# "%s" %s\r\n' % (header,'-'*(75-len(header))))
            #--Topic header?
            elif groupBy == 'topic' and infoKey[1] != prevTopic:
                prevTopic = infoKey[1]
                header = prevTopic or ''
                textFile.write('# "%s" %s\r\n' % (header,'-'*(75-len(header))))
            textFile.write('@ %d "%s" %s' % infoKey)
            if info.spId:
                textFile.write(' "'+info.spId+'"')
            textFile.write('\r\n')
            textFile.write(info.text)
            textFile.write('\r\n')
            textFile.write('\r\n')
        #--Done
        textFile.close()

#------------------------------------------------------------------------------
class FileLibrary(FileRep):
    """File representation for generating library books.
    Generates library books from input text file and current mod load list."""
    def __init__(self, fileInfo,canSave=True,log=None,progress=None):
        """Initialize."""
        self.srcBooks = {} #--srcBooks[srcId] = (bookRecord,modName)
        self.altBooks = {} #--altBooks[altId] = (bookRecord,modName)
        self.libList  = [] #--libId1, libId2, etc. in same order as in text file.
        self.libMap   = {} #--libMap[libId]  = (srcId,altId)
        FileRep.__init__(self,fileInfo,canSave,log,progress)

    def loadUI(self,factory={'GLOB':Glob,'BOOK':Book,'SCPT':Scpt,'CELL':Cell}):
        """Loads data from file."""
        FileRep.loadUI(self,factory)

    def loadText(self,inName):
        """Read library book list from specified text file."""
        reComment = re.compile(r'\s*\#.*')
        ins = file(inName)
        for line in ins:
            #print line,
            #--Strip spaces and comments
            line = reComment.sub('',line)
            line = line.rstrip()
            #--Skip empty/comment lines
            if not line: continue
            #--Parse line
            (libId,srcId,altId) = line.split('\t')[:3]
            self.libList.append(libId)
            self.libMap[libId] = (srcId,altId)
        #--Done
        ins.close()

    def getBooks(self):
        """Extracts source book data from currently loaded mods."""
        srcIds = set([srcId for srcId,altId in self.libMap.values()])
        altIds = set([altId for srcId,altId in self.libMap.values()])
        factory = {'BOOK':Book}
        for modName in mwIniFile.loadOrder:
            print modName
            fileRep = FileRep(modInfos[modName],False)
            fileRep.load(keepTypes=None,factory=factory)
            for record in fileRep.records:
                if record.name == 'BOOK':
                    bookId = record.getId()
                    if bookId in srcIds:
                        print '',bookId
                        self.srcBooks[bookId] = (record,modName)
                    elif bookId in altIds:
                        print '',bookId
                        self.altBooks[bookId] = (record,modName)
    
    def copyBooks(self):
        """Copies non-Morrowind books to self."""
        skipMods = set(('Morrowind.esm',self.fileInfo.name))
        for id,(record,modName) in (self.srcBooks.items() + self.altBooks.items()):
            if modName not in skipMods:
                self.setRecord(copy.copy(record))

    def genLibData(self):
        """Creates new esp with placed refs for lib books. WILL OVERWRITE!"""
        import mush
        tsMain = string.Template(mush.libGenMain)
        tsIfAltId = string.Template(mush.libGenIfAltId)
        #--Data Records
        for id in ('lib_action','lib_actionCount'):
            glob = self.getRecord('GLOB',id,Glob)
            (glob.type, glob.value) = ('s',0)
            glob.setChanged()
        setAllCode  = 'begin lib_setAllGS\n'
        setNoneCode = 'begin lib_setNoneGS\n'
        for libId in self.libList:
            (srcId,altId) = self.libMap[libId]
            srcBook = self.srcBooks.get(srcId)[0]
            if not srcBook:
                print '%s: Missing source: %s' % (libId,srcId)
                continue
            #--Global
            glob = self.getRecord('GLOB',libId+'G',Glob)
            (glob.type, glob.value) = ('s',0)
            glob.setChanged()
            #--Script
            scriptId = libId+'LS'
            script = self.getRecord('SCPT',scriptId,Scpt)
            scriptCode = tsMain.substitute(
                libId=libId, srcId=srcId, ifAltId=(
                    (altId and tsIfAltId.substitute(libId=libId,altId=altId)) or ''))
            script.setCode(scriptCode)
            script.setChanged()
            #--Book
            srcBook.load(unpack=True)
            book = self.getRecord('BOOK',libId,Book)
            book.model = srcBook.model
            book.title = srcBook.title
            book.icon = srcBook.icon
            book.text = srcBook.text
            book.script = scriptId
            book.setChanged()
            #--Set Scripts
            setAllCode  += 'set %sG to 1\n' % (libId,)
            setNoneCode += 'set %sG to 0\n' % (libId,)
        #--Set scripts
        for id,code in (('lib_setAllGS',setAllCode),('lib_setNoneGS',setNoneCode)):
            code += ';--Done\nstopScript %s\nend\n' % (id,)
            script = self.getRecord('SCPT',id,Scpt)
            script.setCode(code)
            script.setChanged()
        
    def genLibCells(self):
        """Generates standard library """
        #--Cell Records
        objNum = 1
        cellParameters = (
            ('East',270,0,0,0,-6),
            ('North',180,270,90,6,0),
            ('South',0,90,90,-6,0),
            ('West',90,0,180,0,6),)
        for name,rx,ry,rz,dx,dy in cellParameters:
            #--Convert to radians.
            rx, ry, rz = [rot*math.pi/180.0 for rot in (rx,ry,rz)]
            #--Create cell
            cellName = 'BOOKS '+name
            cell = self.getRecord('CELL',cellName,Cell)
            cell.cellName = cellName
            (cell.flags,cell.gridX,cell.gridY) = (1,1,1)
            del cell.objects[:]
            del cell.tempObjects[:]
            tempObjects = cell.tempObjects = []
            for index,libId in enumerate(self.libList):
                srcId = self.libMap[libId][0]
                if srcId not in self.srcBooks: continue
                srData = SubRecord('DATA',24)
                srData.setData(struct.pack('6f',index*dx,index*dy,100,rx,ry,rz))
                tempObjects.append((0,objNum,libId,[Cell_Frmr(),srData]))
                objNum += 1
            cell.setChanged()

    def doImport(self,textFile):
        """Does all the import functions."""
        self.loadText(textFile)
        self.getBooks()
        #self.copyBooks()
        self.genLibData()
        self.genLibCells()
        self.sortRecords()

#------------------------------------------------------------------------------
class FileLists(FileRep):
    """TES3 file representation focussing on levelled lists.

    Only TES3 LEVI and LEVC records are analyzed. All others are left in raw data 
    form. """
    def __init__(self, fileInfo, canSave=True):
        FileRep.__init__(self,fileInfo,canSave)
        self.levcs = {}
        self.levis = {}
        self.srcMods = {} #--Used by merge functionality

    def load(self):
        """Load leveled lists from file."""
        canSave = self.canSave
        #--Header
        inPath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        ins = Tes3Reader(self.fileInfo.name,file(inPath,'rb'))
        (name,size,delFlag,recFlag) = ins.unpack('4s3i',16,'REC_HEAD')
        self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        #--Raw data read
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            #--LEVC?
            if name == 'LEVC':
                levc = Levc(name,size,delFlag,recFlag,ins,True)
                self.levcs[levc.id] = levc
                if canSave: self.records.append(levc)
                #print '  Added:',levc.id
            elif name == 'LEVI':
                levi = Levi(name,size,delFlag,recFlag,ins,True)
                self.levis[levi.id] = levi
                if canSave: self.records.append(levi)
                #print '  Added:',levi.id
            #--Other
            elif canSave:
                record = Record(name,size,delFlag,recFlag,ins)
                self.records.append(record)
            else:
                ins.seek(size,1,'Record')
        #--Done Reading
        ins.close()

    def beginMerge(self):
        """Begins merge process. """
        #--Delete existing lists.
        listTypes = set(['LEVC','LEVI'])
        self.records = [record for record in self.records if record.name not in listTypes]
        self.levcs.clear()
        self.levis.clear()

    def mergeWith(self, newFL):
        """Add lists from another FileLists object."""
        srcMods = self.srcMods
        for levls, newLevls in ((self.levcs,newFL.levcs),(self.levis,newFL.levis)):
            for listId, newLevl in newLevls.items():
                if listId not in srcMods: 
                    srcMods[listId] = [newFL.fileInfo.name]
                    levl = levls[listId] = copy.deepcopy(newLevl)
                    self.records.append(levl)
                else:
                    srcMods[listId].append(newFL.fileInfo.name)
                    levls[listId].mergeWith(newLevl)

    def completeMerge(self):
        """Completes merge process. Use this when finished using mergeWith."""
        #--Remove lists that aren't the sum of at least two esps.
        srcMods = self.srcMods
        for levls in (self.levcs,self.levis):
            for listId in levls.keys():
                if len(srcMods[listId]) < 2 or levls[listId].isDeleted:
                    self.records.remove(levls[listId])
                    del levls[listId]
                    del srcMods[listId]
        #--Log
        log = self.log
        for label, levls in (('Creature',self.levcs), ('Item',self.levis)):
            if not len(levls): continue
            log.setHeader(_('Merged %s Lists:') % (label,))
            for listId in sorted(levls.keys(),key=lambda a: a.lower() ):
                log(listId)
                for mod in srcMods[listId]:
                    log('  '+mod)

#------------------------------------------------------------------------------
class FileScripts(FileRep):
    """TES3 file representation focussing on scripts. Only scripts are analyzed.
    All other recods are left in raw data form."""
    def __init__(self, fileInfo, canSave=True):
        FileRep.__init__(self,fileInfo,canSave)
        self.scripts = []

    def load(self,factory={}):
        """Load dialogs from file."""
        canSave = self.canSave
        #--Header
        inPath = os.path.join(self.fileInfo.dir,self.fileInfo.name)
        ins = Tes3Reader(self.fileInfo.name,file(inPath,'rb'))
        (name,size,delFlag,recFlag) = ins.unpackRecHeader()
        self.tes3 = Tes3(name,size,delFlag,recFlag,ins,True)
        #--Raw data read
        dial = None
        while not ins.atEnd():
            #--Get record info and handle it
            (name,size,delFlag,recFlag) = ins.unpackRecHeader()
            #--SCPT?
            if name == 'SCPT':
                record = Scpt(name,size,delFlag,recFlag,ins,True)
                self.scripts.append(record)
                if canSave: self.records.append(record)
            #--Non-dials?
            elif canSave:
                record = Record(name,size,delFlag,recFlag,ins)
                self.records.append(record)
            else:
                ins.seek(size,1,'Record')
        #--Done Reading
        ins.close()

    def save(self,outPath=None):
        """Save data to file. 
        outPath -- Path of the output file to write to. Defaults to original file path."""
        if (not self.canSave): raise StateError(_("Insufficient data to write file."))
        FileRep.save(self,outPath)

    def loadText(self,textFileName):
        """Replaces dialog text with text read from file."""
        textFile = file(textFileName,'rb')
        reHeader = re.compile('^# ([a-zA-Z_0-9]+)')
        id,lines,changed = None,[],[]
        id_records = dict((record.id.lower(),record) for record in self.scripts)
        def unBuffer():
            record = id and id_records.get(id.lower())
            if record:
                code = (''.join(lines)).strip()
                if code.lower() != record.sctx.data.strip().lower():
                    record.setCode(code)
                    changed.append(id)
        for line in textFile:
            maHeader = reHeader.match(line)
            if maHeader:
                unBuffer()
                id,lines = maHeader.group(1),[]
            elif id: 
                lines.append(line)
        textFile.close()
        unBuffer()
        return sorted(changed,key=string.lower)

    def dumpText(self,textFileName):
        """Dumps dialogs to file."""
        textFile = file(textFileName,'wb')
        for script in sorted(self.scripts, key=lambda a: a.id.lower()):
            textFile.write('# %s %s\r\n' % (script.id,'='*(76 - len(script.id))))
            textFile.write(script.sctx.data.strip())
            textFile.write('\r\n\r\n')
        textFile.close()

# Processing Functions, Classes -----------------------------------------------
#------------------------------------------------------------------------------
class CharSetImporter:
    """Imports CharSets from text file to mod."""
    def __init__(self):
        self.log = Log()
        self.classStats = {}

    def loadText(self,fileName):
        """TextMunch: Reads in 0/30 level settings and spits out a level setting script."""
        #--Constants
        reComment = re.compile(';.*')
        reClassName = re.compile(r'@\s*([a-zA-Z0-9_]+)')
        reStats = re.compile(r'\s*(\d+)\s+(\d+)')
        statNames = ('Agility', 'Block', 'Light Armor', 'Marksman', 'Sneak', 'Endurance', 'Heavy Armor', 'Medium Armor', 'Spear', 'Intelligence', 'Alchemy', 'Conjuration', 'Enchant', 'Security', 'Personality', 'Illusion', 'Mercantile', 'Speechcraft', 'Speed', 'Athletics', 'Hand To Hand', 'Short Blade', 'Unarmored', 'Strength', 'Acrobatics', 'Armorer', 'Axe', 'Blunt Weapon', 'Long Blade', 'Willpower', 'Alteration', 'Destruction', 'Mysticism', 'Restoration', 'Luck',)
        #--Read file
        inn = open(fileName)
        curStats = className = None
        for line in inn:
            stripped = reComment.sub('',line).strip()
            maClassName = reClassName.match(stripped)
            maStats = reStats.match(stripped)
            if not stripped: 
                pass
            elif maClassName:
                className = maClassName.group(1)
                curStats = self.classStats[className] = []
            elif maStats:
                v00,v30 = [int(stat) for stat in maStats.groups()]
                curStats.append((v00,v30))
            else:
                raise MoshError(_('Bad line in CharSet class file.')+line.strip()+' >> '+stripped)
        inn.close()
        #--Post Parse
        for className,stats in self.classStats.items():
            if len(stats) != 35:
                raise MoshError(_('Bad number of stats for class ')+className)
            stats = self.classStats[className] = dict(zip(statNames,stats))
            #--Health
            str00,str30 = stats['Strength']
            end00,end30 = stats['Endurance']
            hea00 = (str00 + end00)/2
            hea30 = (str30 + end30)/2 + end30*29/10
            stats['Health'] = (hea00,hea30)

    def printMajors(self):
        """Print major and minor skills for each class."""
        import mush
        skills = mush.combatSkills+mush.magicSkills+mush.stealthSkills
        for className, stats in sorted(self.classStats.items()):
            print className,'-------------------------------'
            skillStats = [(key,value) for key,value in stats.items() if key in skills]
            skillStats.sort(key=lambda a: a[1][1],reverse=True)
            for low,high in ((0,5),(5,10)):
                for skill,stat in sorted(skillStats[low:high]):
                    print '%-13s  %3d' % (skill,stat[1])
                print

    def save(self,fileInfo):
        """Add charset scripts to esp."""
        fileRep = FileRep(fileInfo)
        fileRep.load(factory={'SCPT':Scpt})
        fileRep.unpackRecords(set(('SCPT',)))
        fileRep.indexRecords(set(('SCPT',)))
        #--Add scripts
        for className in self.classStats.keys():
            print className
            id = 'wr_lev%sGS' % (className,)
            script = fileRep.getRecord('SCPT',id,Scpt)
            script.setCode(self.getScript(className))
        #--Done
        fileRep.sortRecords()
        fileRep.safeSave()

    def getScript(self,className):
        """Get stat setting script for classname."""
        #--Constants
        import mush
        charSet0 = string.Template(mush.charSet0)
        charSet1 = string.Template(mush.charSet1)
        reSpace = re.compile(r'\s+')
        statGroups = (
            ('Primary',mush.primaryAttributes),
            ('Secondary',('Health',)),
            ('Combat Skills',mush.combatSkills),
            ('Magic Skills',mush.magicSkills),
            ('Stealth Skills',mush.stealthSkills))
        #--Dump Script
        stats = self.classStats[className]
        out = cStringIO.StringIO()
        out.write(charSet0.substitute(className=className))
        for group,statNames in statGroups:
            out.write(';--'+group+'\n')
            for statName in statNames:
                shortName = reSpace.sub('',statName)
                v00,v30 = stats[statName]
                if v00 == v30:
                    out.write('set%s %d\n' % (shortName,v00,))
                else:
                    out.write('  set stemp to %d + ((%d - %d)*level/30)\n' % (v00,v30,v00))
                    out.write('set%s stemp\n' % (shortName,))
            out.write('\n')
        out.write(charSet1.substitute(className=className))
        return out.getvalue()

#------------------------------------------------------------------------------
class ScheduleGenerator:
    """Generates schedules from input text files."""
    def __init__(self):
        import mush
        self.log = Log()
        #--Project
        self.project = None
        #--Definitions
        #  defs[key] = string
        self.defs = {}
        self.defs.update(dictFromLines(mush.scheduleDefs,re.compile(r':\s+')))
        #--Code
        #  code[town] = [[lines0],[lines1],[lines2]...]
        #  lines0 used for all cycles
        self.code = {}
        #--Sleep (sleep, lighting, etc.)
        #  sleep[town][cycle] = [(cell1,state1),(cell2,state2),...]
        #  state = '-' (not sleeping), '+' (sleeping)
        self.sleep = {}
        #--Schedule
        #  schedule[town][npc] = [(condition1,[act1,act2,act3,act4]),(condition2,[...])]
        #  actN = (posString,aiString)
        self.schedule = {} 
        #--New towns. I.e., towns that just imported.
        self.newTowns = set()
        #--Template Strings
        self.tsMaster = string.Template(mush.scheduleMaster)
        self.tsCycle1 = string.Template(mush.scheduleCycle1)
        self.tsSleep0 = string.Template(mush.scheduleSleep0)
        self.tsSleep1 = string.Template(mush.scheduleSleep1)
        self.tsSleep2 = string.Template(mush.scheduleSleep2)
        self.tsReset0 = string.Template(mush.scheduleReset0)
        self.tsReset1 = string.Template(mush.scheduleReset1)
        self.tsReset2 = string.Template(mush.scheduleReset2)

    #--Schedule
    def loadText(self,fileName,pickScheduleFile=None,imported=None):
        """Read schedule from file."""
        #--Localizing
        defs = self.defs
        log = self.log
        #--Re's
        reCell = re.compile("\s*(\".*?\")")
        reCodeCycle = re.compile("\s*([1-4][ ,1-4]*)")
        reComment = re.compile(r'\s*\#.*')
        reDef = re.compile(r'\.([a-zA-Z]\w+)')
        rePos = re.compile("-?\d+\s+-?\d+\s+-?\d+\s+-?\d+")
        reRepeat = re.compile('= (\d)')
        reSleep = re.compile(r'([=+\-\*\^~x])\s+(.+)$')
        reWander = re.compile('wander +(\d+)')
        reIsMember = re.compile('isMember +(".+")')
        #--Functions/Translators
        replDef = lambda a: defs[a.group(1)]
        #--0: awake, 1: sleep+trespass, 2: sleep 3: dim trespass
        sleepStates = {'=':None,'-':0,'+':1,'*':2,'^':3,'~':4,'x':5} 
        #--Log
        header = os.path.split(fileName)[-1]
        if len(header) < 70: header += '='*(70-len(header))
        log.setHeader(header)
        #--Imported
        isTopFile = (imported == None)
        if isTopFile: imported = []
        #--Input variables
        section = None
        town = None
        townNpcs = set()
        townSchedule = None
        npcSchedule = None
        codeCycles = [0]
        #--Parse input file
        ins = file(fileName)
        for line in ins:
            #log(line.strip())
            #print line,
            #--Strip spaces and comments
            line = reComment.sub('',line)
            line = line.rstrip()
            #--Skip empty/comment lines
            if not line: continue
            #--Section header?
            if line[0] == '@':
                # (town|defs|night|code|npcName)[: npcCondition]
                parsed = line[1:].split(':',1)
                id = parsed[0].strip()
                #--Non-npc?
                if id in set(['town','defs','night','evening','code','import','project']):
                    section = id
                    if section in ('evening','night'):
                        townSleep = self.sleep[town]
                    elif section == 'code':
                        cycles = [0]
                        townCode = self.code[town] = [[],[],[],[],[]]
                else:
                    section = 'npc'
                    npc = id
                    #--Any town,npc combination will overwrite any town,npc 
                    #  combination from an imported file.
                    if (town,npc) not in townNpcs:
                        townNpcs.add((town,npc))
                        townSchedule[npc] = []
                    npcSchedule = [0,0,0,0]
                    condition = (len(parsed) == 2 and parsed[1].strip())
                    townSchedule[npc].append((condition,npcSchedule))
                if section not in set(('town','import','project')): 
                    log('  '+line[1:])
            #--Data 
            else:
                #--Import
                if section == 'import':
                    newPath = line.strip()
                    log(_('IMPORT: ')+newPath)
                    if not os.path.exists(newPath) and pickScheduleFile:
                        caption = "Find sub-import file %s:" % (newPath,)
                        newPath = pickScheduleFile(caption,newPath)
                    if not (newPath and os.path.exists(newPath)):
                        raise StateError("Unable to import schedule file: "+line.strip())
                    if newPath.lower() in [dir.lower() for dir in imported]:
                        log(_('  [%s already imported.]') % (newPath,))
                    else:
                        log.indent += '> '
                        imported.append(newPath)
                        self.loadText(newPath,pickScheduleFile,imported)
                        log.indent = log.indent[:-2]
                #--Project
                elif section == 'project' and isTopFile:
                    self.project = line.strip()
                    log(_('PROJECT: ')+self.project)
                #--Defs 
                elif section == 'defs':
                    (key,value) = line.strip().split(':',1)
                    defs[key] = value.strip()
                #--Town
                elif section == 'town':
                    town = line.strip()
                    log.setHeader(town)
                    if isTopFile:
                        self.newTowns.add(town)
                    if town not in self.schedule:
                        self.schedule[town] = {}
                        self.sleep[town] =  {3:{},4:{}} 
                    townSchedule = self.schedule[town]
                    npcSchedule = None
                    codeCycles = []
                #--Code
                elif section == 'code':
                    line = reDef.sub(replDef,line)
                    maCodeCycle = reCodeCycle.match(line)
                    if maCodeCycle:
                        codeCycles = [int(x) for x in maCodeCycle.group(1).split(',')]
                        continue
                    for cycle in codeCycles:
                        townCode[cycle].append(line)
                #--Evening/Night
                elif section in ('evening','night'):
                    cycle = {'evening':3,'night':4}[section]
                    line = reDef.sub(replDef,line)
                    chunks = [chunk.strip() for chunk in line.split(';')]
                    maSleep = reSleep.match(chunks[0])
                    if not maSleep: continue
                    (cell,defaultState) = (maSleep.group(2), sleepStates[maSleep.group(1)])
                    cellStates = (defaultState,)
                    for chunk in chunks[1:]:
                        chunk = chunk.strip()
                        maSleep = reSleep.match(chunk)
                        if not maSleep or maSleep.group(1) == '=': 
                            raise MoshError(_('Bad sleep condition state for %s in %s: %s') 
                                % (section,town,line))
                        condition,state = maSleep.group(2), sleepStates[maSleep.group(1)]
                        condition = reIsMember.sub(r'getPCRank \1 >= 0',condition)
                        cellStates += ((condition,state),)
                    townSleep[cycle][cell] = cellStates
                #--NPC
                elif section == 'npc':
                    #--Get Cycle
                    cycle = int(line[0])
                    rem = line[2:]
                    #--Repeater?
                    maRepeat = reRepeat.match(rem)
                    if maRepeat:
                        oldCycle = int(maRepeat.group(1))
                        npcSchedule[cycle-1] = npcSchedule[oldCycle-1]
                        continue
                    #--Replace defs
                    rem = reDef.sub(replDef,rem)
                    #--Cell
                    maCell = reCell.match(rem)
                    if not maCell:
                        raise MoshError(_('Pos cell not defined for %s %s %d') % (town,npc,cycle))
                    cell = maCell.group(1)
                    rem = rem[len(cell):].strip()
                    #--Pos
                    maPos = rePos.match(rem)
                    coords = maPos.group(0).strip().split()
                    coords[-1] = `int(coords[-1])*57` #--Workaround interior rotation bug
                    pos = 'positionCell %s %s' % (' '.join(coords),cell)
                    rem = rem[len(maPos.group(0)):].strip()
                    #--Wander/Travel
                    ai = reWander.sub(r'wander \1 5 10  ',rem)
                    #--Save
                    npcSchedule[cycle-1] = (pos,ai)
        ins.close()

    def dumpText(self,fileName):
        """Write schedule to file."""
        out = file(fileName,'w')
        for town in sorted(self.towns):
            #--Header
            out.write('; '+town+' '+'='*(76-len(town))+'\n')
            #--Cycle Scripts
            for cycle in [1,2,3,4]:
                out.write(self.getCycleScript(town,cycle))
                out.write('\n')
            #--Master, cells scripts
            out.write(self.getSleepScript(town,3))
            out.write('\n')
            out.write(self.getSleepScript(town,4))
            out.write('\n')
            out.write(self.getMasterScript(town))
            out.write('\n')
        out.close()

    def save(self,fileInfo):
        """Add schedule scripts to esp."""
        fileRep = FileRep(fileInfo)
        fileRep.load(factory={'SCPT':Scpt,'DIAL':Dial,'INFO':Info})
        fileRep.unpackRecords(set(('SCPT',)))
        fileRep.indexRecords(set(('SCPT',)))
        #--Add scripts
        def setScript(id,code):
            script = fileRep.getRecord('SCPT',id,Scpt)
            script.setCode(code)
        for town in sorted(self.newTowns):
            #--Cycle Scripts
            for cycle in (1,2,3,4):
                setScript('SC_%s_%d' % (town,cycle), self.getCycleScript(town,cycle))
            #--Master, sleep scripts
            for cycle in (3,4):
                setScript('SC_%s_C%d' % (town,cycle), self.getSleepScript(town,cycle))
            setScript('SC_%s_Master' % (town,), self.getMasterScript(town))
        #--Reset Scripts
        if self.project:
            setScript('SC_%s_ResetGS' % (self.project,), self.getResetScript())
            setScript('SC_%s_ResetStatesGS' % (self.project,), self.getResetStatesScript())
        #--Add dialog scripts
        #--Find Hello entries
        recIndex = 0
        records = fileRep.records
        while recIndex < len(records):
            record = records[recIndex]
            recIndex += 1
            if isinstance(record,Dial):
                record.load(unpack=True)
                if record.type == 1 and record.id == 'Hello': break
        #--Sub scripts into hello entries
        reSCInit = re.compile(r'^;--SC_INIT: +(\w+)',re.M)
        while recIndex < len(records):
            record = records[recIndex]
            recIndex += 1
            if record.name != 'INFO': break
            record.load(unpack=True)
            script = record.script
            if not script: continue
            maSCInit = reSCInit.search(script)
            #--No SCInit marker in script?
            if not maSCInit: continue
            town = maSCInit.group(1)
            #--SCInit for uncovered town?
            if town not in self.newTowns: continue
            #--Truncate script and add npc initializers
            script = script[:maSCInit.end()]
            for npc in sorted(self.schedule[town].keys()):
                script += '\r\nset SC_temp to "%s".nolore' % (npc,)
            script += '\r\nset SC_%s_State to -1' % (town,)
            script += '\r\n;messagebox "Initialized %s"' % (town,)
            #--Save changes
            record.script = winNewLines(script)
            record.setChanged()
        #--Done
        fileRep.sortRecords()
        fileRep.safeSave()

    def getResetScript(self):
        """Return SC_[Project]_ResetGS script."""
        if not self.project: raise StateError(_('No project has been defined!'))
        text = self.tsReset0.substitute(project=self.project)
        for town in sorted(self.schedule.keys()):
            text += self.tsReset1.substitute(town=town)
        text += self.tsReset2.substitute(project=self.project)
        return text

    def getResetStatesScript(self):
        """Return SC_[Project]_ResetStatesGS script."""
        if not self.project: raise StateError(_('No project has been defined!'))
        text = "begin SC_%s_ResetStatesGS\n" % (self.project,)
        text += ';--Sets state variables for %s project to zero.\n' % (self.project,)
        for town in sorted(self.schedule.keys()):
            text += 'set SC_%s_State to 0\n' % (town,)
        text += "stopScript SC_%s_ResetStatesGS\nend\n" % (self.project,)
        return text

    def getMasterScript(self,town):
        """Return master script for town."""
        c3 = iff(self.sleep[town][3],'',';')
        c4 = iff(self.sleep[town][4],'',';')
        return self.tsMaster.substitute(town=town,c3=c3,c4=c4)

    def getSleepScript(self,town,cycle):
        """Return cells ("C") script for town, cycle."""
        out = cStringIO.StringIO()
        tcSleep = self.sleep[town][cycle]
        #--No cells defined? 
        if len(tcSleep) == 0:
            out.write(self.tsSleep0.substitute(town=town,cycle=cycle))
        else:
            out.write(self.tsSleep1.substitute(town=town,cycle=cycle))
            #--Want to sort so that generic names are last. (E.g. "Vos" after "Vos, Chapel")
            #  But sort also needs to ignore leading and trailing quotes in cell string.
            #  So, compare trimmed cell string, and then reverse sort.
            for cell in sorted(tcSleep.keys(),key=lambda a: a[1:-1],reverse=True):
                cellStates = tcSleep[cell]
                defaultState = cellStates[0]
                out.write('elseif ( getPCCell %s )\n' % (cell,))
                if defaultState == None: continue
                for count,(condition,state) in enumerate(cellStates[1:]):
                    ifString = ['if','elseif'][count > 0]
                    out.write('\t%s ( %s )\n\t\tset SC_Sleep to %s\n' % (ifString,condition,state))
                if len(cellStates) > 1:
                    out.write('\telse\n\t\tset SC_Sleep to %s\n\tendif\n' % (defaultState,))
                else:
                    out.write('\tset SC_Sleep to %s\n' % (defaultState,))
            out.write(self.tsSleep2.substitute(town=town,cycle=cycle))

        return out.getvalue()

    def getCycleScript(self,town,cycle):
        """Return cycle script for town, cycle."""
        #--Schedules
        reWanderCell = re.compile('wander[, ]+(\d+)',re.I)
        rePosCell = re.compile('positionCell +(\-?\d+) +(\-?\d+) +(\-?\d+).+"(.+)"')
        townCode = self.code.get(town,0)
        townSchedule = self.schedule[town]
        npcs = sorted(townSchedule.keys())
        townCode
        out = cStringIO.StringIO()
        cycleCode = ''
        if townCode:
            for line in townCode[0]+townCode[cycle]:
                cycleCode += '\t'+line+'\n'
        out.write(self.tsCycle1.substitute(town=town,cycle=`cycle`,cycleCode=cycleCode))
        for npc in npcs:
            out.write('if ( "%s"->getDisabled )\n' % (npc,))
            out.write('elseif ( "%s"->getItemCount SC_offSchedule != 0 )\n' % (npc,))
            for (condition,npcSchedule) in townSchedule[npc]:
                if condition == False:
                    out.write('else\n')
                else:
                    out.write('elseif ( %s )\n' % (condition,))
                (pos,ai) = npcSchedule[cycle-1]
                out.write('\tif ( action < 20 )\n')
                out.write('\t\t"%s"->%s\n' % (npc,pos))
                if ai != 'NOAI':
                    #--Wandering in exterior cell?
                    maWanderCell = reWanderCell.match(ai)
                    maPosCell = rePosCell.match(pos)
                    if maWanderCell and (int(maWanderCell.group(1)) > 0) and (maPosCell.group(4).find(',') == -1):
                        xx,yy,zz,cell = maPosCell.groups()
                        out.write('\t\t"%s"->aiTravel %s %s %s\n' % (npc,xx,yy,zz))
                        out.write('\t\tset action to 10\n\telse\n')
                    out.write('\t\t"%s"->ai%s\n' % (npc,ai))
                out.write('\tendif\n')
            out.write('endif\n')
        out.write("if ( action != 10 )\n\tset action to 20\nendif\n")
        out.write('end\n')
        return out.getvalue()

# Initialization --------------------------------------------------------------
#-# Modified by D.C.-G.
#-# Avoiding error return on installers path creation not allowed.
#-#     I implemented this because my installers directory is on a remote drive ;-)
#-# ==>> ONLY FOR WINDOWS
#-# Errors skipped:
#-#   * path not accessible pysically (missing drive or unaccessible URL);
#-#   * the user does not have the rights to write in the destination folder.
#------------------------------------------------------------------------------
def initDirs():
    """Init directories. Assume that settings has already been initialized."""
    #--Bash Ini
    mashIni = None
    if GPath('mash.ini').exists():
        mashIni = ConfigParser.ConfigParser()
        mashIni.read('mash.ini')
    dirs['app'] = GPath(settings['mwDir'])
    dirs['mods'] = dirs['app'].join('Data Files')
    #--Installers
    if mashIni and mashIni.has_option('General','sInstallersDir'):
        installers = GPath(mashIni.get('General','sInstallersDir').strip())
    else:
        installers = GPath('Installers')
    if installers.isabs():
        dirs['installers'] = installers
    else:
        dirs['installers'] = dirs['app'].join(installers)
    #-# D.C.-G.
    # dirs['installers'].makedirs()

    # prevHead = ""
    # head = dirs['installers'].s
    # print sys.platform
    # print "prevHead", prevHead, "head", head
    # while prevHead != head:
        # prevHead = head
        # head, tail = os.path.split(prevHead)
        # print "head", head, "tail", tail
    # detecting Windows
    if sys.platform.lower().startswith("win") == True:
        drv, pth = os.path.splitdrive(dirs['installers'].s)
        if os.access(drv, os.R_OK):
            #-# Testing the directories
            # class Dummy: chk = None

            # def testDir(a, d, ds):
                # if d in dirs['installers'].s:
                    # Dummy.chk = os.access(d, a)

            # os.path.walk(dirs['installers'].s, testDir, os.F_OK)
            # print "chk", Dummy.chk
            #-#
            # print "Installers directory found."
            dirs['installers'].makedirs()
    #-#

#------------------------------------------------------------------------------
def initSettings(path='settings.pkl'):
    global settings
    settings = Settings(path)
    reWryeMash = re.compile('^wrye\.mash')
    for key in settings.data.keys():
        newKey = reWryeMash.sub('mash',key)
        if newKey != key:
            settings[newKey] = settings[key]
            del settings[key]
    settings.loadDefaults(settingDefaults)

# Main ------------------------------------------------------------------------
if __name__ == '__main__':
    print _('Compiled')
