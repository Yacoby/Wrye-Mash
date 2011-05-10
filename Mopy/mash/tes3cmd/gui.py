import os
from copy import copy

import wx

from .. import tes3cmd
from . import tes3cmdgui


class OutputParserMixin:
    """
    Thi is a mixin to allow unit testing, as we cannot initiate Cleaner
    without a lot of faf with wx
    """
    def ParseOutput(self, output):
        """ Parses the output for a single mod """
        stats   = ''
        cleaned = ''
        inStats = False

        for line in output.split('\n'):
            if inStats and line.strip():
                stats += line.strip() + '\n'
            elif line.strip().startswith('Cleaned'):
                cleaned += line.strip() + '\n'
            elif line.strip().startswith('Cleaning Stats for'):
                inStats = True
            elif line.strip().endswith('was not modified'):
                stats += line + '\n'

        return stats, cleaned


class CleanOp( tes3cmdgui.cleanop ):
	def __init__( self, parent ):
		tes3cmdgui.cleanop.__init__( self, parent )
	
	def OnCancel( self, event ):
		pass
	
	def OnCleanClick( self, event ):
		pass


#the thread that manages the threaded process uses wx events
#to post messsages to the main thread
EVT_DONE_ID = wx.NewId()
def EVT_DONE(win, func):
    win.Connect(-1, -1, EVT_DONE_ID, func)

class DoneEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(EVT_DONE_ID)


class Cleaner(tes3cmdgui.cleaner, OutputParserMixin):
    """
    GUI interface for the clean function
    

    It holds a list of files to clean. When Start() is called it works down the
    list of files by calling StartNext which pops a file off the list of files 
    and processes it. When the processing of that file is finished OnDone is
    called 
    """

    def __init__(self, parent, files, args = {}):
        """
        parent - Parent window
        files - list of files to clean
        args - arguemtns to pass to the tes3cmd.threaded class
        """
        tes3cmdgui.cleaner.__init__(self, parent)

        self.args = args

        self.files = files
        self.totalFiles = len(files)

        self.output = {}

        EVT_DONE(self,self.OnDone)

    def Start(self, callback=None):
        """
        Starts running tes3cmd over all the files

        callback - The function that is called when the process is complete
        """
        self.endCallback = callback
        self.StartNext()

    def StartNext(self):
        """ 
        Starts processing the next file on the list of files. If there are no
        files to process this calls the callback function as defined in the
        call to Start()

        This is called from Start() to start cleaning the list of files
        and from OnDone to start cleaning the next file when one has been
        cleaned.
        """

        if not self.files:
            self.mSkip.Disable()
            self.mStop.Disable()
            if self.endCallback:
                self.endCallback()
            return

        filename = self.files.pop()
        lowerFname = filename.lower()

        #we don't want to clean morrowind.esm
        if lowerFname == 'morrowind.esm':
            self.StartNext()
            return

        #if we copy expansions, don't clean gmsts (I think)
        args = copy(self.args)
        if lowerFname == 'tribunal.esm' or lowerFname == 'bloodmon.esm':
            args['gmsts'] = False
        args['replace'] = True

        self.mCurrentFile.SetLabel(filename)

        self.worker = tes3cmd.Threaded(callback=lambda: wx.PostEvent(self, DoneEvent()))
        self.worker.clean([filename], **args)
    
    def OnDone(self, event):
        """
        Called when a file has finished processing. This parses the output
        and starts cleaning the next mod
        """
        out = self.worker.out
        err = self.worker.err
        
        stats, cleaned = self.ParseOutput(out)
        for f in self.worker.files:
            self.output[f] = { 'stats' : stats,
                               'cleaned' : cleaned,
                               'output' : out,
                               'error' : err }
            self.mCleanedMods.Append(f)

        if not self.mCleanedMods.GetSelections():
            self.mCleanedMods.Select(0)
            self.Select(self.worker.files[0])

        ratio = (self.totalFiles - len(self.files))/float(self.totalFiles)
        self.mProgress.SetValue(ratio*100)

        self.mCurrentFile.SetLabel('')
        self.StartNext()
	
    def OnSkip(self, event):
        """ When the skip button is pressed """
        self.worker.stop()
        self.worker.join()

        self.StartNext()

    def OnStop(self, event):
        """ When the stop button is pressed """
        self.worker.stop()
        self.worker.join()

    def Select(self, name):
        """ Sets the details for the given mod name """
        item = self.output[name]
        self.mStats.SetLabel(item['stats'])
        self.mLog.SetValue(item['cleaned'])
        self.mErrors.SetValue(item['error'])

    def OnSelect(self, event):
        """ ListBox select, selecting a mod to view the stats of """
        self.Select(event.GetString())

    def SaveLog(self, fileName):
        """ Saves the log information to the given location """
        f = open(fileName, 'w')
        for o in self.output.values(): 
            if o['error']:
                f.write(o['error'])
                f.write('\n')
            if o['output']:
                f.write(o['output'])
                f.write('\n')
        f.close()

    def OnSaveLog(self, event):
        dlg = wx.FileDialog(self, 'Save log', os.getcwd(),
                            'tes3cmd.log', '*.log',
                            wx.SAVE | wx.OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            fileName = os.path.join(dlg.GetDirectory(), dlg.GetFilename())
            self.SaveLog(fileName)

