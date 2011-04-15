import wx
import wx.html
import os
import wtexparser
from balt import spacer, vSizer, leftSash
from mosh import _

class TocHtmlWindow(wx.TreeCtrl):
    """Contains the table of content of the help file.
    Typically, this is the left panel of the help window."""

    def SetHtmlData(self, data):
        """data : str : html text"""
        p = wtexparser.Parser()
        p.parseString(data)

        if  len(p.root.children) == 1:
            child = p.root.children[0]
            self.treeRoot = self.AddRoot(child.title)
            self.AddToTree(child, self.treeRoot)
        else:
            self.treeRoot = self.AddRoot('Help')
            self.AddToTree(self.root, self.treeRoot)
        self.Expand(self.treeRoot)
        self.SelectItem(self.treeRoot, True)

    def AddSelListener(self, f):
        """
            This, when given a funcction will call that function with the name of the
            newly selected item when the selection changes
        """
        def PrepForSending(func, event):
            item = event.GetItem()
            func(self.GetItemText(item))

        self.Bind(wx.EVT_TREE_SEL_CHANGED, lambda e: PrepForSending(f,e))
 
    def AddToTree(self, docNode, treeNode):
        for child in docNode.children:
            newTreeNode = self.AppendItem(treeNode, child.title)
            self.AddToTree(child, newTreeNode)


class HelpPage(wx.html.HtmlWindow):
    """Class for the pages of the help window.
    Typically, this is the right panel of the help window."""

    def SetHtmlData(self, data):
        """data : str : html text"""
        self.parser = wtexparser.Parser()
        self.parser.parseString(data)

    def OnLinkClicked(self, link):
        href = link.GetHref()
        if href[:1] != '#':
            wx.LaunchDefaultBrowser(href)
        else:
            wx.html.HtmlWindow.OnLinkClicked(self, link)

    def TocSelChanged(self, name):
        heading = self.parser.getHeading(name) 
        if heading != None:
            self.SetPage(wtexparser.getHtmlFromHeadings(heading))
        else:
            self.SetPage('')

class HelpBrowser(wx.Frame):
    """Help Browser frame."""
    def __init__(self, mashFrame,images, settings):
        """Intialize."""
        self.settings = settings

        #--Data
        self.data = None
        self.counter = 0
        #--Singleton
        global helpBrowser
        helpBrowser = self
        #--Window
        pos  = settings.get('mash.help.pos',(-1,-1))
        size = settings.get('mash.help.size',(400,600))

        wx.Frame.__init__(self, mashFrame, -1, _('Help'), pos, size, style=wx.DEFAULT_FRAME_STYLE)

        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        #--Application Icons
        self.SetIcons(images['mash.icons2'].GetIconBundle())

        #--Sizers
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        sashPos = 250
        if 'mash.help.sashPos' in settings:
            sashPos = settings['mash.help.sashPos']
        left  = self.left  = leftSash(self,defaultSize=(sashPos,100),onSashDrag=self.OnSashDrag)
        right = self.right =  wx.Panel(self,style=wx.NO_BORDER)

        self.htmlContent = TocHtmlWindow(left, -1, style = wx.NO_FULL_REPAINT_ON_RESIZE)
        self.htmlText    = HelpPage(right, -1, style = wx.NO_FULL_REPAINT_ON_RESIZE)


        left.SetSizer(vSizer((self.htmlContent, 1, wx.GROW)))
        right.SetSizer(vSizer((self.htmlText, 1, wx.GROW|wx.ALIGN_RIGHT|wx.EXPAND)))

        mainSizer.Add(left,1,wx.GROW)
        mainSizer.Add(right,5,wx.GROW)
        #--Layout
        self.SetSizer(mainSizer)
        #--Events
        wx.EVT_CLOSE(self, self.OnCloseWindow)

        #--Content
        self.htmlContent.AddSelListener(self.htmlText.TocSelChanged)
        path = os.path.join(os.getcwd(), 'Wrye Mash.txt')
        txt  = open(path).read()
        self.htmlText.SetHtmlData(txt)
        self.htmlContent.SetHtmlData(txt)


        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def OnSashDrag(self,event):
        """Handle sash moved."""
        wMin,wMax = 80,self.GetSizeTuple()[0]-80
        sashPos = max(wMin,min(wMax,event.GetDragRect().width))
        self.left.SetDefaultSize((sashPos,10))
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        # screensList.picture.Refresh()
        self.settings['mash.help.sashPos'] = sashPos


    #--Window Closing
    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        self.settings['mash.help.show'] = False
        if not self.IsIconized() and not self.IsMaximized():
            self.settings['mash.help.pos'] = self.GetPosition()
            self.settings['mash.help.size'] = self.GetSizeTuple()
        self.Destroy()
