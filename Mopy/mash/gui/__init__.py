import pickle

import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin

from .. import globals
from .. import exception

from .. import balt
from .. import mosh
from ..mosh import _

#constant
wxListAligns = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT, wx.LIST_FORMAT_CENTRE]

class LoggerWindow(wx.Frame):
    """
    Alters the logger so that it doesn't write to stdout/stderr but to 
    a dialog box
    """
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, wx.ID_ANY, title)
        panel = wx.Panel(self, wx.ID_ANY)
        self.txtLog = wx.TextCtrl(panel, wx.ID_ANY, size=(300,100),
                          style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.txtLog, 1, wx.ALL|wx.EXPAND, 5)
        panel.SetSizer(sizer)

    def write(self, message):
        self.txtLog.WriteText(message)

    def writeLine(self, message):
        self.txtLog.WriteText(message + '\n')


class InterfaceError(exception.MashError):
    pass

# ------------------------------------------------------------------------------

class ListDragDropMixin:
    '''
    This allows the simple dragging and dropping in lists, although this doesn't
    allow dragging between lists

    Due to the design of other parts of the program this doesn't acutally
    move the item in the list and leaves it up to the implementation of
    OnDrop to do that work
    '''
    def __init__(self, listCtrl):
        listCtrl.Bind(wx.EVT_LIST_BEGIN_DRAG, self._DoStartDrag)
        self.listCtrl = listCtrl

        dt = ListDrop(listCtrl.GetId(), self._DdInsert)
        self.listCtrl.SetDropTarget(dt)

    def OnDrop(self, names, startIndex):
        '''
        The event for an item being dropped, should be overridden

        names - The names of the item (its text)
        startIndex - The index that the items should be inserted
        '''
        pass

    def _DoStartDrag(self, e):
        selected = []

        idx = -1
        while True: # find all the selected items and put them in a list
            idx = self.listCtrl.GetNextItem(idx,
                                            wx.LIST_NEXT_ALL,
                                            wx.LIST_STATE_SELECTED)
            if idx == -1:
                break
            selected.append(self.listCtrl.GetItemText(idx))

        data = wx.CustomDataObject('ListItems%d' % self.listCtrl.GetId())
        data.SetData(pickle.dumps(selected))

        ds = wx.DropSource(self.listCtrl)
        ds.SetData(data)
        ds.DoDragDrop(True)

    def _DdInsert(self, x, y, selected):
        '''
        Insert text at given x, y coordinates --- used with drag-and-drop.
        '''
        # Find insertion point.
        toIdx, flags = self.listCtrl.HitTest((x, y))

        if toIdx == wx.NOT_FOUND:
            if flags & wx.LIST_HITTEST_NOWHERE:
                toIdx = self.listCtrl.GetItemCount()
            else:
                return

        # Get bounding rect for the item being dropped onto and if the user is
        # dropping into the lower half of the rect, we want to insert _after_ this item.
        rect = self.listCtrl.GetItemRect(toIdx)
        if y > rect.y + rect.height/2:
            toIdx += 1

        self.OnDrop(selected, toIdx)

        #ensure the moved items are selected
        for itemDex in range(self.listCtrl.GetItemCount()):
            self.listCtrl.SetItemState(itemDex, 0, wx.LIST_STATE_SELECTED)

        idx = -1
        while True:
            idx = self.listCtrl.GetNextItem(idx, wx.LIST_NEXT_ALL)
            if idx == -1: 
                break
            elif self.listCtrl.GetItemText(idx) in selected:
                self.listCtrl.Select(idx);


class ListDrop(wx.PyDropTarget):
    ''' Drop target for simple lists. '''

    def __init__(self, dataId, setFn):
        '''
        dataId - The id of the list, this ensures that we can't dragdrop between lists
        setFn - Function to call on drop.
        '''
        wx.PyDropTarget.__init__(self)

        self.setFn = setFn

        # specify the type of data we will accept
        self.data = wx.CustomDataObject('ListItems%d' % dataId)
        self.SetDataObject(self.data)

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        # copy the data from the drag source to our data object
        if self.GetData():
            selected = pickle.loads(self.data.GetData())
            self.setFn(x, y, selected)

        # what is returned signals the source what to do
        # with the original data (move, copy, etc.)  In this
        # case we just return the suggested value given to us.
        return d

# ------------------------------------------------------------------------------

class ListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style=style)
        ListCtrlAutoWidthMixin.__init__(self)


class List(wx.Panel):
    def __init__(self,parent,id=-1,ctrlStyle=(wx.LC_REPORT | wx.LC_SINGLE_SEL)):
        wx.Panel.__init__(self,parent,id, style=wx.WANTS_CHARS)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.SetSizeHints(-1,50)
        #--ListCtrl
        listId = self.listId = wx.NewId()
        self.list = ListCtrl(self, listId, style=ctrlStyle)
        self.checkboxes = globals.images['mash.checkboxes']
        #--Columns
        self.PopulateColumns()
        #--Items
        self.sortDirty = 0
        self.PopulateItems()
        #--Events
        wx.EVT_SIZE(self, self.OnSize)
        #--Events: Items
        self.hitIcon = 0
        wx.EVT_LEFT_DOWN(self.list,self.OnLeftDown)
        wx.EVT_COMMAND_RIGHT_CLICK(self.list, listId, self.DoItemMenu)
        #--Events: Columns
        wx.EVT_LIST_COL_CLICK(self, listId, self.DoItemSort)
        wx.EVT_LIST_COL_RIGHT_CLICK(self, listId, self.DoColumnMenu)
        wx.EVT_LIST_COL_END_DRAG(self,listId, self.OnColumnResize)

    #--Items ----------------------------------------------
    #--Populate Columns
    def PopulateColumns(self):
        """Create/name columns in ListCtrl."""
        cols = self.cols
        self.numCols = len(cols)
        for colDex in range(self.numCols):
            colKey = cols[colDex]
            colName = self.colNames.get(colKey,colKey)
            wxListAlign = wxListAligns[self.colAligns.get(colKey,0)]
            self.list.InsertColumn(colDex,colName,wxListAlign)
            self.list.SetColumnWidth(colDex, self.colWidths.get(colKey,30))

    def PopulateItem(self,itemDex,mode=0,selected=set()):
        """Populate ListCtrl for specified item. [ABSTRACT]"""
        raise mosh.AbstractError

    def GetItems(self):
        """Set and return self.items."""
        self.items = self.data.keys()
        return self.items

    def PopulateItems(self,col=None,reverse=-2,selected='SAME'):
        """Sort items and populate entire list."""
        #--Sort Dirty?
        if self.sortDirty:
            self.sortDirty = 0
            (col, reverse) = (None,-1)
        #--Items to select afterwards. (Defaults to current selection.)
        if selected == 'SAME': selected = set(self.GetSelected())
        #--Reget items
        self.GetItems()
        self.SortItems(col,reverse)
        #--Delete Current items
        listItemCount = self.list.GetItemCount()
        #--Populate items
        for itemDex in range(len(self.items)):
            mode = int(itemDex >= listItemCount)
            self.PopulateItem(itemDex,mode,selected)
        #--Delete items?
        while self.list.GetItemCount() > len(self.items):
            self.list.DeleteItem(self.list.GetItemCount()-1)

    def ClearSelected(self):
        for itemDex in range(self.list.GetItemCount()):
            self.list.SetItemState(itemDex, 0, wx.LIST_STATE_SELECTED)

    def GetSelected(self):
        """Return list of items selected (hilighted) in the interface."""
        #--No items?
        if not 'items' in self.__dict__: return []
        selected = []
        itemDex = -1
        while True:
            itemDex = self.list.GetNextItem(itemDex,
                wx.LIST_NEXT_ALL,wx.LIST_STATE_SELECTED)
            if itemDex == -1: 
                break
            else:
                selected.append(self.items[itemDex])
        return selected

    def SelectItems(self, items):
        itemDex = -1
        while True:
            itemDex = self.list.GetNextItem(itemDex, wx.LIST_NEXT_ALL)
            if itemDex == -1: 
                break
            elif self.items[itemDex] in items:
                self.list.Select(itemDex);

    def SelectAll(self):
        itemDex = -1
        while True:
            itemDex = self.list.GetNextItem(itemDex, wx.LIST_NEXT_ALL)
            if itemDex == -1: 
                break
            else:
                self.list.Select(itemDex);

    #$# from FallenWizard
    def DeleteSelected(self):
        """Deletes selected items."""
        items = self.GetSelected()
        if items:
            message = _(r'Delete these items? This operation cannot be undone.')
            message += '\n* ' + '\n* '.join(x for x in sorted(items))
            if balt.askYes(self,message,_('Delete Items')):
                for item in items:
                    self.data.delete(item)
            globals.modList.Refresh()
    #$#

    def GetSortSettings(self,col,reverse):
        """Return parsed col, reverse arguments. Used by SortSettings.
        col: sort variable. 
        Defaults to last sort. (self.sort)
        reverse: sort order
        1: Descending order
        0: Ascending order
        -1: Use current reverse settings for sort variable, unless
            last sort was on same sort variable -- in which case, 
            reverse the sort order. 
        -2: Use current reverse setting for sort variable.
        """
        #--Sort Column
        if not col:
            col = self.sort
        #--Reverse
        oldReverse = self.colReverse.get(col,0)
        if col == 'Load Order': #--Disallow reverse for load
            reverse = 0
        elif reverse == -1 and col == self.sort:
            reverse = not oldReverse
        elif reverse < 0:
            reverse = oldReverse
        #--Done
        self.sort = col
        self.colReverse[col] = reverse
        return (col,reverse)

    #--Event Handlers -------------------------------------
    #--Column Menu
    def DoColumnMenu(self,event):
        if not self.mainMenu: return
        #--Build Menu
        column = event.GetColumn()
        menu = wx.Menu()
        for link in self.mainMenu:
            link.AppendToMenu(menu,self,column)
        #--Show/Destroy Menu
        self.PopupMenu(menu)
        menu.Destroy()

    #--Column Resize
    def OnColumnResize(self,event):
        pass

    #--Item Sort
    def DoItemSort(self, event):
        self.PopulateItems(self.cols[event.GetColumn()],-1)

    #--Item Menu
    def DoItemMenu(self,event):
        selected = self.GetSelected()
        if not selected: return
        #--Build Menu
        menu = wx.Menu()
        for link in self.itemMenu:
            link.AppendToMenu(menu,self,selected)
        #--Show/Destroy Menu
        self.PopupMenu(menu)
        menu.Destroy()

    #--Size Change
    def OnSize(self, event):
        size = self.GetClientSizeTuple()
        #print self,size
        self.list.SetSize(size)

    #--Event: Left Down
    def OnLeftDown(self,event):
        #self.hitTest = self.list.HitTest((event.GetX(),event.GetY()))
        event.Skip()

# ------------------------------------------------------------------------------

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
