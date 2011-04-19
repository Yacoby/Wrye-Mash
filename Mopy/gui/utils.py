import os
import sys

import wx

import globals
import conf
import gui.dialog
import mosh

from balt import button, Links, leftSash, hSizer, vSizer
from mosh import _
from types import *

class FakeColumnEvent:
    """..."""
    def __init__(self, numCols):
        """..."""
        self.column = numCols

    def GetColumn(self):
        """..."""
        return self.column


class UtilsPanel(gui.NotebookPanel):
    """Utilities tab."""
    def __init__(self,parent):
        """Initialize."""
        wx.Panel.__init__(self, parent, -1)
        #--Left
        sashPos = conf.settings.get('bash.screens.sashPos',120)
        left = self.left = leftSash(self,defaultSize=(sashPos,100),onSashDrag=self.OnSashDrag)
        right = self.right =  wx.Panel(self,style=wx.NO_BORDER)
        #--Contents
        globals.utilsList = UtilsList(left)
        globals.utilsList.SetSizeHints(100,100)
        # screensList.picture = balt.Picture(right,256,192)
        #--Events
        self.Bind(wx.EVT_SIZE,self.OnSize)
        #--Layout
        left.SetSizer(hSizer((globals.utilsList,1,wx.GROW),((10,0),0)))
        self.gCommandLine = wx.TextCtrl(right,-1)
        self.gArguments = wx.TextCtrl(right,-1)
        self.gDescription = wx.TextCtrl(right,-1,style=wx.TE_MULTILINE)
        globals.utilsList.commandLine = self.gCommandLine
        globals.utilsList.arguments = self.gArguments
        globals.utilsList.description = self.gDescription
        right.SetSizer(vSizer((self.gCommandLine,0,wx.GROW),
                        (self.gArguments,0,wx.GROW),
                        (self.gDescription,1,wx.GROW)))
        wx.LayoutAlgorithm().LayoutWindow(self, right)

    def SetStatusCount(self):
        """Sets status bar count field."""
        # text = _('Screens: %d') % (len(screensList.data.data),)
        # statusBar.SetStatusText(text,2)

    def OnSashDrag(self,event):
        """Handle sash moved."""
        wMin,wMax = 80,self.GetSizeTuple()[0]-80
        sashPos = max(wMin,min(wMax,event.GetDragRect().width))
        self.left.SetDefaultSize((sashPos,10))
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)
        # screensList.picture.Refresh()
        conf.settings['bash.screens.sashPos'] = sashPos

    def OnSize(self,event=None):
        wx.LayoutAlgorithm().LayoutWindow(self, self.right)

    def OnShow(self):
        """Panel is shown. Update self.data."""
        if mosh.utilsData.refresh():
            globals.utilsList.RefreshUI()
        self.SetStatusCount()


class UtilsList(gui.List):
    #--Class Data
    mainMenu = Links() #--Column menu
    itemMenu = Links() #--Single item menu

    def __init__(self,parent):
        #--Columns
        self.cols = conf.settings['bash.screens.cols']
        self.colAligns = conf.settings['bash.screens.colAligns']
        self.colNames = conf.settings['mash.colNames']
        self.colReverse = conf.settings.getChanged('bash.screens.colReverse')
        self.colWidths = conf.settings['bash.screens.colWidths']
        #--Data/Items
        self.data = mosh.utilsData = mosh.UtilsData()
        self.sort = conf.settings['bash.screens.sort']
        #--Links
        self.mainMenu = UtilsList.mainMenu
        self.itemMenu = UtilsList.itemMenu
        #--Parent init
        gui.List.__init__(self,parent,-1,ctrlStyle=(wx.LC_REPORT|wx.SUNKEN_BORDER))
        #--Events
        wx.EVT_LIST_ITEM_SELECTED(self,self.listId,self.OnItemSelected)
        wx.EVT_LIST_ITEM_ACTIVATED(self,self.listId,self.OnItemActivated)

    def RefreshUI(self,files='ALL',detail='SAME'):
        """Refreshes UI for specified files."""
        #--Details
        if detail == 'SAME':
            selected = set(self.GetSelected())
        else:
            selected = set([detail])
        #--Populate
        if files == 'ALL':
            self.PopulateItems(selected=selected)
        elif isinstance(files,StringTypes):
            self.PopulateItem(files,selected=selected)
        else: #--Iterable
            for file in files:
                self.PopulateItem(file,selected=selected)
        globals.mashFrame.SetStatusCount()

    #--Populate Item
    def PopulateItem(self,itemDex,mode=0,selected=set()):
        #--String name of item?
        if not isinstance(itemDex,int):
            itemDex = self.items.index(itemDex)
        fileName = self.items[itemDex].strip()
        fileInfo = self.data[fileName]
        cols = self.cols
        for colDex in range(self.numCols):
            col = cols[colDex]
            if col == 'File':
                value = fileName
            elif col == 'Modified':
                value = mosh.formatDate(fileInfo[1])
            else:
                value = '-'
            if mode and (colDex == 0):
                self.list.InsertStringItem(itemDex, value)
            else:
                self.list.SetStringItem(itemDex, colDex, value)
        #--Image
        #--Selection State
        if fileName in selected:
            self.list.SetItemState(itemDex,wx.LIST_STATE_SELECTED,wx.LIST_STATE_SELECTED)
        else:
            self.list.SetItemState(itemDex,0,wx.LIST_STATE_SELECTED)

    #--Sort Items
    def SortItems(self,col=None,reverse=-2):
        (col, reverse) = self.GetSortSettings(col,reverse)
        conf.settings['bash.screens.sort'] = col
        data = self.data
        #--Start with sort by name
        self.items.sort()
        if col == 'File':
            pass #--Done by default
        elif col == 'Modified':
            self.items.sort(key=lambda a: data[a][1])
        else:
            raise BashError(_('Unrecognized sort key: ')+col)
        #--Ascending
        if reverse: self.items.reverse()

    #--Events ---------------------------------------------
    #--Column Resize
    def OnColumnResize(self,event):
        colDex = event.GetColumn()
        colName = self.cols[colDex]
        self.colWidths[colName] = self.list.GetColumnWidth(colDex)
        conf.settings.setChanged('bash.screens.colWidths')

    def OnItemSelected(self,event=None):
        """..."""
        name = event.GetText()
        if name in self.data.keys():
            self.commandLine.SetValue(self.data[name][0])

            self.arguments.SetValue(self.data[name][1])
            desc = self.data[name][2]
            if (desc.startswith('"') and desc.endswith('"')) or (desc.startswith("'") and desc.endswith("'")):
                self.description.SetValue(eval(desc))
            else:
                self.description.SetValue(desc)

    def OnItemActivated(self, event=None):
        """Launching the utility."""
        name = event.GetText()
        if name in self.data.keys():
            u = self.data[name][0]
            try:
                if u.lower() == "mish":
                    import mish
                    argsList = self.data[name][1].split()
                    sys_argv_org = sys.argv
                    mish.sys.argv = ["mish"] + argsList
                    print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\nMISH output.\n\nArguments: %s\n"%self.arguments.Value
                    mish.callables.main()
                    sys.argv = sys_argv_org
                    #
                    return # <-- bad hack ?

                cwd = os.getcwd()
                os.chdir(os.path.dirname(u))
                if u.strip('"').strip("'")[-4:].lower() in (".bat", ".cmd", ".btm"):
                    arguments = ""
                    argsList = self.data[name][1].split()
                    if len(argsList) >0:
                        for a in argsList:
                            arguments += " %s"%a
                    os.system(u+arguments)
                else:
                    arguments = (os.path.basename(u),) + tuple(self.data[name][1].split())
                    os.spawnv(os.P_NOWAIT, u.strip('"'), arguments)
                os.chdir(cwd)
            except Exception, exc:
                gui.dialog.WarningMessage(self, _("A problem has occured when opening `%s`.\nYou should edit `utils.dcg` and update the corresponding line.\n\nError shouted by OS:\n%s"%(u, exc)))
                raise exc

    def NewItem(self):
        """Adds a new utility to the list."""
        dialog = UtilsDialog(self, new=True)
        if dialog.ShowModal() != wx.ID_OK:
            dialog.Destroy()
            return
        result = dialog.result
        if result:
            if result[0] not in ("", None) and result[1] not in ("", None):
                self.data[result[0]] = result[1:]
                self.data.save()
                self.DoItemSort(FakeColumnEvent(0))
                self.RefreshUI()

    def ModifyItem(self):
        """Modification of an item.
        This function modifies an item or does nothing."""
        names = self.GetSelected()
        item = self.list.GetFirstSelected()
        # for name in names:
        idx = 0
        while idx < len(names):
            name = names[idx]
            dialog = UtilsDialog(self, new=False, data=((name,) + self.data[name]))
            if dialog.ShowModal() != wx.ID_OK:
                dialog.Destroy()
                return
            result = dialog.result
            if result:
                if result[0] not in ("", None) and result[1] not in ("", None):
                    if result[0] != name:
                        self.list.DeleteItem(item)
                        self.data.pop(name)
                        listItem = wx.ListItem()
                        listItem.SetText(result[0])
                        self.list.InsertItem(listItem)
                    self.data[result[0]] = result[1:]
                    self.data.save()
            idx += 1
            item = self.list.GetNextSelected(item)
        self.DoItemSort(FakeColumnEvent(0))
        self.RefreshUI()

    def DeleteItem(self):
        """Deletes an item.
        This function deletes the selected item or does nothing."""
        names = self.GetSelected()
        for name in names:
            self.list.DeleteItem(self.list.GetFirstSelected())
            self.data.pop(name)
        self.data.save()
        self.commandLine.SetValue("")
        self.arguments.SetValue("")
        self.description.SetValue("")
        self.DoItemSort(FakeColumnEvent(0))
        self.RefreshUI()


class UtilsDialog(wx.Dialog):
    """Dialog for crating/modifying utilities.
    Has several text captions for name, program (with browse button), arguments and description."""
    result = None
    def __init__(self, parent, pos=wx.DefaultPosition, size=(400, wx.DefaultSize[1]), new=True, data = ("","","","")):
        """..."""
        wx.Dialog.__init__(self, parent, pos=pos, size=size, style=wx.DEFAULT_FRAME_STYLE)
        self.Panel = wx.Panel(self)
        self.SetMinSize(size)
        sepV1 = (0,1)
        sepV2 = (0,2)
        # components
        txtName = wx.StaticText(self.Panel, -1, _("Name"))
        self.fldName = wx.TextCtrl(self.Panel, -1, value=data[0])
        txtProg = wx.StaticText(self.Panel, -1, _("Program"))
        self.fldProg = wx.TextCtrl(self.Panel, -1, value=data[1])
        btnBrowse = button(self.Panel, id=-1, label=_("..."), name="btnBrowse", onClick=self.OpenFile, tip=_("Browse for a program."))
        txtArguments = wx.StaticText(self.Panel, -1, _("Arguments"))
        self.fldArguments = wx.TextCtrl(self.Panel, -1, value=data[2])
        txtDesc = wx.StaticText(self.Panel, -1, _("Description"))
        self.fldDesc = wx.TextCtrl(self.Panel, -1, style=wx.TE_MULTILINE, value=data[3])
        btnOk = button(self.Panel, id=wx.ID_OK, label=_("OK"), name="btnOk", onClick=self.SaveUtility)
        btnCancel = button(self.Panel, id=wx.ID_CANCEL, label=_("Cancel"), name="btnCancel", onClick=self.Cancel)
        # sizers
        sizerProg = wx.BoxSizer(wx.HORIZONTAL)
        sizerProg.AddMany([(self.fldProg,1,wx.EXPAND),((2,0)),(btnBrowse)])
        sizerBtn = wx.BoxSizer(wx.HORIZONTAL)
        sizerBtn.AddMany([(btnOk,0,wx.EXPAND),((2,0),0,wx.EXPAND),(btnCancel,0,wx.EXPAND)])
        sizerWin = wx.BoxSizer(wx.VERTICAL)
        sizerWin.AddMany([(txtName),(sepV1),(self.fldName,0,wx.EXPAND),(sepV2),(txtProg),(sepV1),(sizerProg,0,wx.EXPAND),(sepV2),
                    (txtArguments),(sepV1),(self.fldArguments,0,wx.EXPAND),(sepV2),(txtDesc),(sepV1),(self.fldDesc, 1, wx.EXPAND),(sepV2),
                    (sizerBtn,0,wx.EXPAND)])
        sizerWin.Fit(self)
        self.Panel.SetSizer(sizerWin)
        self.Panel.Layout()
        # events
        wx.EVT_BUTTON(self, wx.ID_OK, self.SaveUtility)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.Cancel)

    def Cancel(self, event):
        """Cancels the utility creation/modification."""
        self.result = False
        event.Skip()

    def OpenFile(self, event):
        """Opens the file dialog to set the utility program."""
        dialog = wx.FileDialog(self,_("Chose the new utility."), "", "", "*.*", wx.OPEN)
        if dialog.ShowModal() != wx.ID_OK:
            dialogDestroy()
            return
        path = dialog.GetPath()
        dialog.Destroy()
        self.fldProg.SetValue(path)

    def SaveUtility(self, event):
        """Saves the new/modified utility."""
        name = self.fldName.GetValue()
        prog = self.fldProg.GetValue()
        arguments = self.fldArguments.GetValue()
        desc = self.fldDesc.GetValue()
        self.result = (name, prog, arguments, desc)
        event.Skip()
