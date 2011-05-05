import wx

import tes3cmd
import tes3cmdgui


class cleanop( tes3cmdgui.cleanop ):
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

# Implementing cleaner
class cleaner(tes3cmdgui.cleaner):
    """ GUI interface for the clean function """

    def __init__(self, parent, files):
        tes3cmdgui.cleaner.__init__(self, parent)
        self.files = files
        self.totalFiles = len(files)

        self.output = {}

        EVT_DONE(self,self.OnDone)


    def Start(self, callback=None):
        """
        callback - The function that is called when the process is complete
        """
        self.endCallback = callback
        self.StartNext()


    def StartNext(self):
        """ Starts processing the next file on the list of files """

        if not self.files:
            self.mSkip.Disable()
            self.mStop.Disable()
            if self.endCallback:
                self.endCallback()
            return

        filename = self.files.pop()
        self.mCurrentFile.SetLabel(filename)

        self.worker = tes3cmd.Threaded(callback=lambda: wx.PostEvent(self, DoneEvent()))
        self.worker.clean([filename], replace=True)
    
    def OnDone(self, event):
        """ Called when a file has finished processing """
        out = self.worker.out
        err = self.worker.err
        
        stats, cleaned = self.ParseOutput(out)
        for f in self.worker.files:
            self.output[f] = { 'stats' : stats,
                               'cleaned' : cleaned,
                               'error' : err }
            self.mCleanedMods.Append(f)

        if not self.mCleanedMods.GetSelections():
            self.mCleanedMods.Select(0)

        ratio = (self.totalFiles - len(self.files))/float(self.totalFiles)
        self.mProgress.SetValue(ratio*100)

        self.mCurrentFile.SetLabel('')
        self.StartNext()

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
	
    def OnSkip(self, event):
        self.worker.stop()
        self.worker.join()

        self.StartNext()

    def OnStop(self, event):
        self.worker.stop()
        self.worker.join()

    def OnSelect(self, event):
        """ ListBox select, selecting a mod to view the stats of """
        item = self.output[event.GetString()]
        
        self.mStats.SetLabel(item['stats'])
        self.mLog.SetValue(item['cleaned'])
        self.mErrors.SetValue(item['error'])
