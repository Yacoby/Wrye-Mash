import os

import wx
import wx.html

import conf 
from balt import spacer, vSizer, leftSash
from mosh import _
import wtexparser

class TocHtmlWindow(wx.TreeCtrl):
    """
    Contains the table of content of the help file.
    Typically, this is the left panel of the help window.
    """

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
        This, when given a funcction will call that function with the name of 
        the newly selected item when the selection changes
        """
        def PrepForSending(func, event):
            item = event.GetItem()
            func(self.GetItemText(item))

        self.Bind(wx.EVT_TREE_SEL_CHANGED, lambda e: PrepForSending(f,e))
 
    def AddToTree(self, docNode, treeNode):
        for child in docNode.children:
            newTreeNode = self.AppendItem(treeNode, child.title)
            self.AddToTree(child, newTreeNode)

    def FindItemByText(self, text, currentItem, transform=lambda t:t):
        """
        Searches each node for a text match

        text: the text to mactch
        currentItem: the item to start from
        transform: a method that alters the currentItem text
                   before it is compared with text
        """
        if transform(self.GetItemText(currentItem)) == text:
            return currentItem

        (child, cookie) = self.GetFirstChild(currentItem)
        while child.IsOk():
            itm = self.FindItemByText(text, child, transform) 
            if itm != None:
                return itm
            (child,cookie) = self.GetNextChild(currentItem, cookie)
        return None
        
    def GoTo(self, name):
        """ Selects an item that has a text match with name"""
        item = self.FindItemByText(name,
                                   self.treeRoot,
                                   lambda t: t.replace(' ', ''))
        if item is not None:
            self.SelectItem(item, True)


class HelpPage(wx.html.HtmlWindow):
    """Class for the pages of the help window.
    Typically, this is the right panel of the help window."""

    def SetHtmlData(self, data):
        """data : str : html text"""
        self.parser = wtexparser.Parser()
        self.parser.parseString(data)

    def OnLinkClicked(self, link):
        href = link.GetHref()
        if not href.startswith('#'):
            wx.LaunchDefaultBrowser(href)
        else:
            anchor = href[1:]
            if self.HasAnchor(anchor):
                wx.html.HtmlWindow.OnLinkClicked(self, link)
            else:
                self.toc.GoTo(anchor)

    def SetTocObj(self, toc):
        self.toc = toc

    def TocSelChanged(self, name):
        heading = self.parser.getHeading(name) 
        if heading is not None:
            self.SetPage(wtexparser.getHtmlFromHeadings(heading))
        else:
            self.SetPage('')


class HelpBrowser(wx.Frame):
    """Help Browser frame."""
    def __init__(self, mashFrame,images):
        """Intialize."""

        #--Data
        self.data = None
        self.counter = 0
        #--Singleton
        global helpBrowser
        helpBrowser = self
        #--Window
        pos  = conf.settings.get('mash.help.pos',(-1,-1))
        size = conf.settings.get('mash.help.size',(400,600))

        wx.Frame.__init__(self, mashFrame, -1, _('Help'), pos,
                          size, style=wx.DEFAULT_FRAME_STYLE)

        self.SetBackgroundColour(wx.NullColour)
        self.SetSizeHints(250,250)
        #--Application Icons
        self.SetIcons(images['mash.icons2'].GetIconBundle())

        #--Sizers
        mainSizer = wx.BoxSizer(wx.HORIZONTAL)

        sashPos = 250
        if 'mash.help.sashPos' in conf.settings:
            sashPos = conf.settings['mash.help.sashPos']
        left = self.left = leftSash(self,defaultSize=(sashPos,100),
                                    onSashDrag=self.OnSashDrag)
        right = self.right =  wx.Panel(self,style=wx.NO_BORDER)

        self.htmlToc = TocHtmlWindow(left, -1,
                                     style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.htmlText = HelpPage(right, -1,
                                 style=wx.NO_FULL_REPAINT_ON_RESIZE)


        left.SetSizer(vSizer((self.htmlToc, 1, wx.GROW)))
        right.SetSizer(vSizer((self.htmlText, 1, wx.GROW|wx.ALIGN_RIGHT|wx.EXPAND)))

        mainSizer.Add(left,1,wx.GROW)
        mainSizer.Add(right,5,wx.GROW)
        #--Layout
        self.SetSizer(mainSizer)
        #--Events
        wx.EVT_CLOSE(self, self.OnCloseWindow)

        #--Content
        self.htmlToc.AddSelListener(self.htmlText.TocSelChanged)
        self.htmlText.SetTocObj(self.htmlToc)

        path = os.path.join(os.getcwd(), 'Wrye Mash.txt')
        txt = open(path).read()
        self.htmlText.SetHtmlData(txt)
        self.htmlToc.SetHtmlData(txt)

        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def OnSashDrag(self,event):
        """Handle sash moved."""
        wMin,wMax = 80,self.GetSizeTuple()[0]-80
        sashPos = max(wMin,min(wMax,event.GetDragRect().width))
        self.left.SetDefaultSize((sashPos,10))
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        conf.settings['mash.help.sashPos'] = sashPos

    def OnCloseWindow(self, event):
        """Handle window close event.
        Remember window size, position, etc."""
        conf.settings['mash.help.show'] = False
        if not self.IsIconized() and not self.IsMaximized():
            conf.settings['mash.help.pos'] = self.GetPosition()
            conf.settings['mash.help.size'] = self.GetSizeTuple()
        self.Destroy()
