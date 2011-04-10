#This is here so that exceptions in loading it can be caught
#without needing endless code

import wx.lib.iewin

class TOCHtmlWindow(wx.lib.iewin.IEHtmlWindow):
    """Contains the table of content of the help file.
    Typically, this is the left panel of the help window."""
    def __init__(self, *args, **kwargs):
        """..."""
        wx.lib.iewin.IEHtmlWindow.__init__(self, *args, **kwargs)
        wx.lib.iewin.EVT_BeforeNavigate2(self, wx.ID_ANY, self.OnHyperLink)
        self.data = None
        self.target = None
        self.hhp = None

    OnHyperLink = OnHyperLink

    def SetHtmlData(self, data):
        """data : str : html text"""
        self.data = data
        self.LoadString(self.data)
        self.htmlData = self.GetText()

    SetHtmlHelpParser = SetHtmlHelpParser

    def SetTarget(self, target, defaultView=None):
        """t : wx.lib.iewin.IEHtmlWindow"""
        target.SetHtmlHelpParser(self.hhp)
        self.target = target
        if defaultView:
            self.target.Navigate(defaultView)

    def CallAXMethod(self, *args, **kwargs):
        """..."""
        pass

class HelpPage(wx.lib.iewin.IEHtmlWindow):
    """Class for the pages of the help window.
    Typically, this is the right panel of the help window."""
    def __init__(self, *args, **kwargs):
        """..."""
        wx.lib.iewin.IEHtmlWindow.__init__(self, *args, **kwargs)
        self.hhp = None
        self.target = self
        wx.lib.iewin.EVT_BeforeNavigate2(self, wx.ID_ANY, self.OnHyperLink)

    SetHtmlHelpParser = SetHtmlHelpParser

    OnHyperLink = OnHyperLink

    def Navigate(self, *args, **kwargs):
        """..."""
        if len(args) != 2:
            args += (None,)
        if type(args[0]) != tuple:
            arg1 = args[0]
            arg2 = args[1]
        else:
            arg1 = args[0][0]
            arg2 = args[1]
        self.LoadString(arg1.read())
        if arg2 != None and type(arg2) == str:
            i = 0
            d = arg1.read()
            a = d.lower().find("<body>") + 6
            b = d.lower().find("</body>")
            for line in d[a:b].splitlines():
                if arg2 in line:
                    idx = i
                    txtExt = self.GetFullTextExtent("Jj", font=self.GetFont())
                    # I can't figure how to make the window scroll to the correct position :(
                    self.ScrollWindow(0, idx * txtExt[1], rect=self.GetRect())
                    break
                i += 1

    Navigate2 = Navigate

