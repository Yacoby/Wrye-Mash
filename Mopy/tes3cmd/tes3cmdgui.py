# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version May  2 2011)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx

###########################################################################
## Class cleanop
###########################################################################

class cleanop ( wx.Dialog ):
	
	def __init__( self, parent ):
		wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"tes3cmd Clean", pos = wx.DefaultPosition, size = wx.Size( 429,217 ), style = wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		bSizer2 = wx.BoxSizer( wx.VERTICAL )
		
		bSizer2.SetMinSize( wx.Size( 400,-1 ) ) 
		self.m_checkBox2 = wx.CheckBox( self, wx.ID_ANY, u"clean cell subrecords AMBI,WHGT duped from masters", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_checkBox2.SetValue(True) 
		bSizer2.Add( self.m_checkBox2, 0, wx.ALL, 5 )
		
		self.mCleanDups = wx.CheckBox( self, wx.ID_ANY, u"clean other complete records duped from masters", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.mCleanDups.SetValue(True) 
		bSizer2.Add( self.mCleanDups, 0, wx.ALL, 5 )
		
		self.mCleanEvil = wx.CheckBox( self, wx.ID_ANY, u"clean Evil GMSTs", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.mCleanEvil.SetValue(True) 
		bSizer2.Add( self.mCleanEvil, 0, wx.ALL, 5 )
		
		self.m_checkBox5 = wx.CheckBox( self, wx.ID_ANY, u"clean object instances from cells when duped from masters", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_checkBox5.SetValue(True) 
		bSizer2.Add( self.m_checkBox5, 0, wx.ALL, 5 )
		
		self.m_checkBox6 = wx.CheckBox( self, wx.ID_ANY, u"clean junk cells (no new info from definition in masters)", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_checkBox6.SetValue(True) 
		bSizer2.Add( self.m_checkBox6, 0, wx.ALL, 5 )
		
		bSizer3 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.m_button4 = wx.Button( self, wx.ID_ANY, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer3.Add( self.m_button4, 0, wx.ALL, 5 )
		
		self.m_button5 = wx.Button( self, wx.ID_ANY, u"Clean Selected", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer3.Add( self.m_button5, 0, wx.ALL, 5 )
		
		bSizer2.Add( bSizer3, 1, wx.EXPAND, 5 )
		
		self.SetSizer( bSizer2 )
		self.Layout()
		
		self.Centre( wx.BOTH )
		
		# Connect Events
		self.m_button4.Bind( wx.EVT_BUTTON, self.OnCancel )
		self.m_button5.Bind( wx.EVT_BUTTON, self.OnCleanClick )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnCancel( self, event ):
		event.Skip()
	
	def OnCleanClick( self, event ):
		event.Skip()
	

###########################################################################
## Class cleaner
###########################################################################

class cleaner ( wx.Frame ):
	
	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"tes3cmd Cleaner", pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.CAPTION|wx.CLOSE_BOX|wx.FRAME_FLOAT_ON_PARENT|wx.SYSTEM_MENU|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		
		bSizer8 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_panel4 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer6 = wx.FlexGridSizer( 2, 1, 0, 0 )
		fgSizer6.AddGrowableCol( 0 )
		fgSizer6.AddGrowableRow( 1 )
		fgSizer6.SetFlexibleDirection( wx.BOTH )
		fgSizer6.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		bSizer14 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.mSkip = wx.Button( self.m_panel4, wx.ID_ANY, u"Skip", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer14.Add( self.mSkip, 0, wx.ALL, 5 )
		
		self.mStop = wx.Button( self.m_panel4, wx.ID_ANY, u"Stop", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer14.Add( self.mStop, 0, wx.ALL, 5 )
		
		self.mProgress = wx.Gauge( self.m_panel4, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL )
		bSizer14.Add( self.mProgress, 0, wx.ALL, 5 )
		
		self.m_staticText6 = wx.StaticText( self.m_panel4, wx.ID_ANY, u"Currently Cleaning:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText6.Wrap( -1 )
		bSizer14.Add( self.m_staticText6, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5 )
		
		self.mCurrentFile = wx.StaticText( self.m_panel4, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.mCurrentFile.Wrap( -1 )
		self.mCurrentFile.SetMaxSize( wx.Size( 80,-1 ) )
		
		bSizer14.Add( self.mCurrentFile, 0, wx.ALIGN_CENTER|wx.ALL, 5 )
		
		fgSizer6.Add( bSizer14, 1, wx.EXPAND, 5 )
		
		bSizer7 = wx.BoxSizer( wx.HORIZONTAL )
		
		mCleanedModsChoices = []
		self.mCleanedMods = wx.ListBox( self.m_panel4, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, mCleanedModsChoices, 0 )
		self.mCleanedMods.SetMinSize( wx.Size( 150,-1 ) )
		
		bSizer7.Add( self.mCleanedMods, 0, wx.ALL|wx.EXPAND, 5 )
		
		bSizer81 = wx.BoxSizer( wx.VERTICAL )
		
		fgSizer5 = wx.FlexGridSizer( 3, 1, 0, 0 )
		fgSizer5.AddGrowableCol( 0 )
		fgSizer5.AddGrowableRow( 2 )
		fgSizer5.SetFlexibleDirection( wx.BOTH )
		fgSizer5.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.m_staticText7 = wx.StaticText( self.m_panel4, wx.ID_ANY, u"Cleaning Stats:", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText7.Wrap( -1 )
		fgSizer5.Add( self.m_staticText7, 0, wx.ALL, 5 )
		
		self.mStats = wx.StaticText( self.m_panel4, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.mStats.Wrap( -1 )
		self.mStats.SetMinSize( wx.Size( -1,80 ) )
		
		fgSizer5.Add( self.mStats, 0, wx.ALL, 5 )
		
		self.m_notebook2 = wx.Notebook( self.m_panel4, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_panel1 = wx.Panel( self.m_notebook2, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		fgSizer7 = wx.FlexGridSizer( 1, 1, 0, 0 )
		fgSizer7.AddGrowableCol( 0 )
		fgSizer7.AddGrowableRow( 0 )
		fgSizer7.SetFlexibleDirection( wx.BOTH )
		fgSizer7.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.mLog = wx.TextCtrl( self.m_panel1, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE|wx.TE_READONLY )
		fgSizer7.Add( self.mLog, 0, wx.ALL|wx.EXPAND, 5 )
		
		self.m_panel1.SetSizer( fgSizer7 )
		self.m_panel1.Layout()
		fgSizer7.Fit( self.m_panel1 )
		self.m_notebook2.AddPage( self.m_panel1, u"Output", True )
		self.m_panel2 = wx.Panel( self.m_notebook2, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
		fgSizer9 = wx.FlexGridSizer( 1, 1, 0, 0 )
		fgSizer9.AddGrowableCol( 0 )
		fgSizer9.AddGrowableRow( 0 )
		fgSizer9.SetFlexibleDirection( wx.BOTH )
		fgSizer9.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.mErrors = wx.TextCtrl( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE|wx.TE_READONLY )
		fgSizer9.Add( self.mErrors, 0, wx.ALL|wx.EXPAND, 5 )
		
		self.m_panel2.SetSizer( fgSizer9 )
		self.m_panel2.Layout()
		fgSizer9.Fit( self.m_panel2 )
		self.m_notebook2.AddPage( self.m_panel2, u"Errors", False )
		
		fgSizer5.Add( self.m_notebook2, 1, wx.EXPAND |wx.ALL, 5 )
		
		bSizer81.Add( fgSizer5, 1, wx.EXPAND, 5 )
		
		bSizer7.Add( bSizer81, 1, wx.EXPAND, 5 )
		
		fgSizer6.Add( bSizer7, 1, wx.EXPAND, 5 )
		
		self.m_panel4.SetSizer( fgSizer6 )
		self.m_panel4.Layout()
		fgSizer6.Fit( self.m_panel4 )
		bSizer8.Add( self.m_panel4, 1, wx.EXPAND |wx.ALL, 0 )
		
		self.SetSizer( bSizer8 )
		self.Layout()
		
		self.Centre( wx.BOTH )
		
		# Connect Events
		self.mSkip.Bind( wx.EVT_BUTTON, self.OnSkip )
		self.mStop.Bind( wx.EVT_BUTTON, self.OnStop )
		self.mCleanedMods.Bind( wx.EVT_LISTBOX, self.OnSelect )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnSkip( self, event ):
		event.Skip()
	
	def OnStop( self, event ):
		event.Skip()
	
	def OnSelect( self, event ):
		event.Skip()
	

