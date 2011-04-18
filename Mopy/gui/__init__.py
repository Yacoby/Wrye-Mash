import wx

import globals


class NotebookPanel(wx.Panel):
    """Parent class for notebook panels."""

    def SetStatusCount(self):
        """Sets status bar count field."""
        globals.statusBar.SetStatusText('',2)

    def OnShow(self):
        """To be called when particular panel is changed to and/or shown for first time.
        Default version does nothing, but derived versions might update data."""
        self.SetStatusCount()

    def OnCloseWindow(self):
        """To be called when containing frame is closing. Use for saving data, scrollpos, etc."""
        pass
