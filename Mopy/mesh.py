# -*- coding: cp1252 -*-
#
# mesh.py
#
# Extension for Wrye Mash 0.8.4
#
# (c) D.C.-G. <00:06 14/07/2010>
#
# Published under the exact same terms as the other files of Wrye Mash.
#
# SettingsWindow objects
#
# <13:06 09/08/2010>
#
# Added installers path.
#
import wx

from mosh import _, dirs, GPath

dataMap = {"Inst":"installers", "Mw":"Morrowind"}

class SettingsWindow(wx.MiniFrame):
	"""Class for the settings window."""
	# defining some variables before initialisation
	settings = None
	init = True

	def __init__(self, parent=None, id=-1, size=(wx.DefaultSize[0],-1), pos = wx.DefaultPosition,
				style=wx.DEFAULT_FRAME_STYLE, settings=None):
		"""..."""
		wx.MiniFrame.__init__(self, parent=parent, id=id, size=size, pos=pos, style=style)
		self.EnableCloseButton(False)
		self.SetTitle(_("Wrye Mash Settings"))
		if settings != None:
			self.settings = settings
		else:
			self.settings = {}
		p = self.Panel = wx.Panel(self)
		# components and sizers
		btnOK = wx.Button(p, wx.ID_OK, _("Ok"), name="btnOK")
		btnCancel = wx.Button(p, wx.ID_CANCEL, _("Cancel"), name="btnCancel")
		btnBrowseMw = wx.Button(p, wx.ID_OPEN, _("..."), size=(-1,-1), name="btnBrowseMw")
		boxMwDir = wx.StaticBox(p, -1, _("Morrowind directory"))
		self.fldMw = wx.TextCtrl(p, -1, name="fldMw")
		sizerBoxMwDir = wx.StaticBoxSizer(boxMwDir, wx.HORIZONTAL)
		sizerBoxMwDir.AddMany([(self.fldMw,1,wx.EXPAND),((2,0)),(btnBrowseMw,0)])
		btnBrowseInst = wx.Button(p, wx.ID_OPEN, _("..."), size=(-1,-1), name="btnBrowseInst")
		boxInst = wx.StaticBox(p, -1, _("Mods installers"))
		self.fldInst = wx.TextCtrl(p, -1, name="fldInst")
		sizerBoxInstallersDir = wx.StaticBoxSizer(boxInst, wx.HORIZONTAL)
		sizerBoxInstallersDir.AddMany([(self.fldInst,1,wx.EXPAND),((2,0)),(btnBrowseInst,0)])
		sizerFields = wx.BoxSizer(wx.VERTICAL)
		sizerFields.AddMany([(sizerBoxMwDir,0,wx.EXPAND),((0,2)),(sizerBoxInstallersDir,0,wx.EXPAND)])
		sizerBtn = wx.BoxSizer(wx.HORIZONTAL)
		sizerBtn.AddMany([(btnOK),((2,0),0,wx.EXPAND),(btnCancel)])
		sizerWin = wx.BoxSizer(wx.VERTICAL)
		sizerWin.AddMany([(sizerFields,0,wx.EXPAND),((0,2)),(sizerBtn)])
		p.SetSizer(sizerWin)
		sizer = wx.BoxSizer()
		sizer.Add(p,1,wx.EXPAND)
		self.SetSizer(sizer)
		sizer.Fit(p)
		self.SetSizeHints(self.GetSize()[0], sizerWin.Size[1])
		self.Fit()
		wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)
		wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
		wx.EVT_BUTTON(self, wx.ID_OPEN, self.OnBrowse)
		wx.EVT_SIZE(self, self.OnSize)

	def OnSize(self, event):
		"""..."""
		self.Layout()
		if self.init == True:
			self.SetSizeHints(*self.GetSize())
			self.init = False

	def OnBrowse(self, event):
		"""Chosing Morrowind directory."""
		name = event.EventObject.Name[9:]
		dialog = wx.DirDialog(self, _("%s directory selection")%dataMap[name].capitalize())
		if dialog.ShowModal() != wx.ID_OK:
			dialog.Destroy()
			return
		path = dialog.GetPath()
		dialog.Destroy()
		getattr(self, "fld%s"%name).SetValue(path)

	def OnCancel(self, event):
		"""Cancel button handler."""
		self.Close()

	def OnOk(self, event):
		"""Ok button handler."""
		self.settings["mwDir"] = self.fldMw.GetValue()
		for item in self.Panel.GetChildren():
			if item.Name.startswith("fld") == True and item.Name[3:] in dataMap:
				name = dataMap[item.Name[3:]]
				if name in dirs:
					dirs[name] = GPath(item.GetValue())
		self.Close()

	def Close(self):
		"""..."""
		self.settings["mash.settings.show"] = False
		# self.settings.save()
		wx.MiniFrame.Close(self)

	def SetSettings(self, settings, **kwargs):
		"""External settings change."""
		self.settings = settings
		self.fldMw.SetValue(settings["mwDir"])
		if kwargs != {}:
			for a in kwargs.keys():
				item = getattr(self, "fld%s"%a, None)
				if item:
					item.SetValue(kwargs[a])
