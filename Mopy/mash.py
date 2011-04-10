# Imports ---------------------------------------------------------------------
import sys
# File logger-------------------------------------------------------------------
class ErrorLogger:
    """Class can be used for a writer to write to multiple streams. Duplicated
    in both possible startup files so log can be created without external
    dependacies"""
    def __init__(self, os):
        self.os = os

    def write(self, string):
        for s in self.os:
            s.write(string)
# Setup log file ---------------------------------------------------------------
f = file("WryeMash.log", "w+")
sys.stdout = ErrorLogger([f, sys.__stdout__])
sys.stderr = ErrorLogger([f, sys.__stderr__])
f.write("Wrye Mash Log!\n");

# Functions used in startup ----------------------------------------------------
def CheckWx():
    """Checks wx is installed, and tries to alert the user"""
    try:
        import wx
    except ImportError:
        try:  #the default win install comes with Tkinter iirc...
            import Tkinter
            import tkMessageBox
            tk = Tkinter.Tk()
            tk.withdraw() #hide the main window
            tkMessageBox.showwarning("wxPython Not Found!", "You need to install wxPython. See the Wrye Mash readme for more info")
            tk.destroy()
            sys.exit(1)
        except ImportError:
            print "You need to install wxPython. See the Wrye Mash readme for more info!"
            raise #dump the info to sdterr

def wxMessageBox(caption, message):
    """Creates a messagebox with its own wx application"""
    app = wx.App()
    dlg = wx.MessageDialog(None, message, caption, wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()
    dlg.Destroy()
    app.Destroy()

def ForceWxVersion():
    """Force wxversion for Python 2.4"""
    if sys.version[:3] == '2.4':
        import wxversion
        wxversion.select("2.5.3.1")


# Main ------------------------------------------------------------------------
#This doesn't check if __name__ == '__main__' as it is used by Wrye Mash.pyc
CheckWx();
ForceWxVersion()

import masher

if len(sys.argv) > 1:
    stdOutCode = int(sys.argv[1])
else:
    stdOutCode = -1

masher.InitSettings()
masher.InitLinks()
masher.InitImages()

if stdOutCode >= 0:
    app = masher.MashApp(stdOutCode)
else:
    app = masher.MashApp()

app.MainLoop()
