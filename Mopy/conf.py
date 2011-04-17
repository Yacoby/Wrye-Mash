import os

import wx

from mosh import _

settings = None

settingDefaults = {
    #-# SettingsWindow
    'mash.settings.show':False,
    #--Morrowind Directory
    #get the parent of the current directory
    'mwDir': os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    #--Wrye Mash
    'mash.version': 0,
    'mash.readme': (0,'84 DCG'),
    'mash.framePos': (-1,-1),
    'mash.frameSize': (600,500),
    'mash.frameSize.min': (400,500),
    'mash.page':0,
    #--Wrye Mash: Windows
    'mash.window.sizes': {},
    #--Wrye Mash: Load Lists
    'mash.loadLists.data': {
        'Bethesda ESMs': [
            'Morrowind.esm',
            'Tribunal.esm',
            'Bloodmoon.esm',
            ],
        },
    #--Wrye Mash: Statistics
    'mash.fileStats.cols': ['Type','Count','Size'],
    'mash.fileStats.sort': 'Type',
    'mash.fileStats.colReverse': {
        'Count':1,
        'Size':1,
        },
    'mash.fileStats.colWidths': {
        'Type':50,
        'Count':50,
        'Size':75,
        },
    'mash.fileStats.colAligns': {
        'Count':1,
        'Size':1,
        },
    #-# Added for Utilities page.
    'bash.utils.page':0,
    #-#
    #--Installers
    'bash.installers.page':1,
    'bash.installers.enabled': True,
    'bash.installers.autoAnneal': True,
    'bash.installers.fastStart': True,
    'bash.installers.removeEmptyDirs':True,
    'bash.installers.skipDistantLOD':False,
    'bash.installers.sortProjects':True,
    'bash.installers.sortActive':False,
    'bash.installers.sortStructure':False,
    'bash.installers.conflictsReport.showLower':True,
    'bash.installers.conflictsReport.showInactive':False,
    #--Wrye Bash: Screens
    'bash.screens.cols': ['File'],
    'bash.screens.sort': 'File',
    'bash.screens.colReverse': {
        'Modified':1,
        },
    'bash.screens.colWidths': {
        'File':150,
        'Modified':150,
        'Size':75,
        },
    'bash.screens.colAligns': {},
    #--Wrye Mash: Group and Rating
    'mash.mods.groups': ['Body','Bethesda','Clothes','Creature','Fix','Last','Test','Game','GFX','Location','Misc.','NPC','Quest','Race','Resource','Sound'],
    'mash.mods.ratings': ['+','1','2','3','4','5','=','~'],
    #--Wrye Mash: RefRemovers
    'mash.refRemovers.data': {
        },
    'mash.refRemovers.safeCells': [
        _("Balmora, Caius Cosades' House"),
        _("Indarys Manor"),
        _("Raven Rock, Factor's Estate"),
        _("Rethan Manor"),
        _("Skaal Village, The Blodskaal's House"),
        _("Solstheim, Thirsk"),
        _("Tel Uvirith, Tower Lower"),
        _("Tel Uvirith, Tower Upper"),
        ],
    #--Wrye Mash: RefReplacers
    'mash.refReplacers.data': {
        },
    #--Wrye Mash: Col (Sort) Names
    'mash.colNames': {
        'Author': _('Author'),
        'Cell': _('Cell'),
        'Count': _('Count'),
        'Day': _('Day'),
        'File': _('File'),
        'Rating': _('Rating'),
        'Group': _('Group'),
        'Load Order': _('Load Order'),
        'Modified': _('Modified'),
        'Num': _('Num'),
        'Player': _('Player'),
        'Rating':_('Rating'),
        'Save Name': _('Save Name'),
        'Size': _('Size'),
        'Status': _('Status'),
        'Type': _('Type'),
        'Version': _('Version'),
        },
    #--Wrye Mash: Masters
    'mash.masters.cols': ['File','Num'],
    'mash.masters.esmsFirst': 1,
    'mash.masters.selectedFirst': 0,
    'mash.masters.sort': 'Load Order',
    'mash.masters.colReverse': {},
    'mash.masters.colWidths': {
        'File':80,
        'Num':20,
        },
    'mash.masters.colAligns': {
        'Num':1,
        },
    #--Wrye Mash: Mod Notes
    'mash.modNotes.show': False,
    'mash.modNotes.size': (200,300),
    'mash.modNotes.pos': wx.DefaultPosition,
    #--Wrye Mash: Mod Docs
    'mash.modDocs.show': False,
    'mash.modDocs.size': (300,400),
    'mash.modDocs.pos': wx.DefaultPosition,
    'mash.modDocs.dir': None,
    #--Wrye Mash: Mods
    'mash.mods.cols': ['File','Rating','Group','Modified','Size','Author'],
    'mash.mods.esmsFirst': 1,
    'mash.mods.selectedFirst': 0,
    'mash.mods.sort': 'File',
    'mash.mods.colReverse': {},
    'mash.mods.colWidths': {
        'File':200,
        'Rating':20,
        'Group':20,
        'Rating':20,
        'Modified':150,
        'Size':75,
        'Author':100,
        },
    'mash.mods.colAligns': {
        'Size':1,
        },
    'mash.mods.renames': {},
    #--Wrye Mash: Journal
    'mash.journal.show': False,
    'mash.journal.size': (300,400),
    'mash.journal.pos': wx.DefaultPosition,
    #--Wrye Mash: Save Sets
    'mash.saves.sets': [],
    #--Wrye Mash: Saves
    'mash.saves.cols': ['File','Modified','Size','Save Name','Player','Cell'],
    'mash.saves.sort': 'Modified',
    'mash.saves.colReverse': {
        'Modified':1,
        },
    'mash.saves.colWidths': {
        'File':150,
        'Modified':150,
        'Size':75,
        'Save Name':100,
        'Player':100,
        'Cell':150,
        'Day':30,
        },
    'mash.saves.colAligns': {
        'Size':1,
        },
    #--Wrye Mash: World Map Reapir
    'mash.worldMap.gridLines':True,
    }

