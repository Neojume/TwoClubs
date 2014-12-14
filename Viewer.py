#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
'''
Implementation of a viewer application to view .result files.

Copyright (C) 2012  Steven Laan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see http://www.gnu.org/licenses/
'''

import wx
import wx.lib.mixins.listctrl as listmix
import  wx.grid as gridlib

import os
import sys
import networkx as nx
import cPickle as pickle

import matplotlib
matplotlib.use('WXAgg')

import matplotlib.pyplot as plt
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar

from Util import TYPE_COTERIE_SEP, TYPE_COTERIE_NONSEP, TYPE_SOCIAL_CIRCLE, TYPE_HAMLET, CLUB_TYPES

VERSION = '5.0'

class TwoClubViewer(wx.Frame):

    '''
    The 2-club viewer application main class.
    '''

    def __init__( self, *args, **kwds):
        kwds['style'] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.all_info = None
        self.nt_threshold = 0
        self.club_contents = []

        # Dictionary containing the different clubs to display
        self.display_clubs = dict()
        for t in CLUB_TYPES:
            self.display_clubs[t] = []

        # Menu Bar
        self.menubar = wx.MenuBar()
        self.file = wx.Menu()
        self.open = wx.MenuItem(self.file, wx.ID_OPEN, '&Open\tCtrl-O', 'Open a .result file', wx.ITEM_NORMAL)
        self.file.AppendItem(self.open)
        self.quit = wx.MenuItem(self.file, wx.ID_EXIT, 'Quit', 'Exit the program', wx.ITEM_NORMAL)
        self.file.AppendItem(self.quit)

        self.edit = wx.Menu()
        self.select_none = wx.MenuItem( self.edit, wx.NewId(), 'Select &None\tCtrl-Shift-A', 'Deselect all nodes', wx.ITEM_NORMAL)
        self.change_threshold = wx.MenuItem(self.edit, wx.NewId(), 'Change &Threshold', 'Change the nontrivial-threshold', wx.ITEM_NORMAL)
        self.edit.AppendItem(self.select_none)
        self.edit.AppendItem(self.change_threshold)

        self.tools = wx.Menu()
        self.importance = wx.MenuItem(self.tools, wx.NewId(), 'Importance graph', 'Create an importance graph of the current result file', wx.ITEM_NORMAL)
        self.coverage = wx.MenuItem(self.tools, wx.NewId(), 'Coverage table', 'Create the coverage table for the different types', wx.ITEM_NORMAL)
        self.largest_clubs = wx.MenuItem(self.tools, wx.NewId(), 'Largest clubs', 'Show largest clubs and maximum degrees', wx.ITEM_NORMAL)
        self.number_clubs = wx.MenuItem(self.tools, wx.NewId(), 'Number of club types', 'Show the number of different club types', wx.ITEM_NORMAL)
        self.tools.AppendItem(self.importance)
        self.tools.AppendItem(self.coverage)
        self.tools.AppendItem(self.largest_clubs)
        self.tools.AppendItem(self.number_clubs)

        self.view = wx.Menu()
        self.view_nontrivials = wx.MenuItem(self.edit, wx.NewId(), 'View non-trivials', 'Show the nontrivial 2-clubs in the list', wx.ITEM_CHECK)
        self.view.AppendItem(self.view_nontrivials)

        self.help = wx.Menu()

        self.menubar.Append(self.file, '&File')
        self.menubar.Append(self.edit, '&Edit')
        self.menubar.Append(self.tools, '&Tools')
        self.menubar.Append(self.view, '&View')
        self.menubar.Append(self.help, '&Help')
        self.SetMenuBar(self.menubar)
        # Menu Bar end

        self.statusbar = self.CreateStatusBar(1, 0)

        self.window_all = wx.SplitterWindow(self, -1, style = wx.SP_3D | wx.SP_BORDER)

        self.notebook_BN = wx.Notebook(self.window_all, -1, style = 0)
        self.panel_all = wx.Panel(self.notebook_BN, -1)
        self.panel_boroughs = wx.Panel(self.notebook_BN, -1 )
        self.panel_nodes = wx.Panel(self.notebook_BN, -1)

        self.clb_nodes = wx.CheckListBox(self.panel_nodes, -1, choices = [])
        self.lb_boroughs = wx.ListBox(self.panel_boroughs, -1, choices = [])
        self.sizer_n_staticbox = wx.StaticBox(self.panel_nodes, -1, 'Nodes')
        self.sizer_b_staticbox = wx.StaticBox(self.panel_boroughs, -1, 'Boroughs')

        self.window_all_pane_2 = wx.Panel(self.window_all, -1)

        self.nb_clubs = wx.Notebook(self.window_all_pane_2, -1, style = 0)
        self.window_club_display = wx.SplitterWindow(self.nb_clubs, -1, style = wx.SP_3D | wx.SP_BORDER)
        self.nb_club_info = wx.Notebook(self.window_club_display, -1, style = 0)
        self.panel_vis = wx.Panel(self.nb_club_info, -1)
        self.tc_club_info = wx.TextCtrl(self.nb_club_info, -1, '', style = wx.TE_MULTILINE)
        self.panel_club_display = wx.Panel(self.window_club_display, -1)
        self.lc_clubs = ClubListCtrlPanel(self.panel_club_display)

        # Dictionary containing selection boxes
        self.display_cbs = dict()
        for t in CLUB_TYPES:
            self.display_cbs[t] = wx.CheckBox(self.panel_club_display, -1, t)

        self.panel_diff = DiffPanel(self.nb_club_info)

        #self.fig = Figure((5.0, 4.0), dpi=100)
        self.fig = plt.figure(figsize=(5.0,4.0), dpi=100)
        self.canvas = FigCanvas(self.panel_vis, -1, self.fig)

        self.axes = self.fig.add_subplot(111)
        self.axes.clear()

        self.toolbar = NavigationToolbar(self.canvas)

        self.__set_properties()
        self.__do_layout()
        #self.Maximize()

    def __set_properties(self):
        self.SetTitle('2-Club Viewer')
        self.statusbar.SetStatusWidths([-1])
        self.statusbar.SetStatusText('Load a file to begin', 0)

        self.lb_boroughs.SetMinSize((128,32))
        #self.panel_club_display.SetMinSize( (224,32) )
        #self.lc_clubs.SetMinSize( (128,32) )
        #self.nb_clubs.SetMinSize( (512,320) )

        # Tick all boxes
        for t in CLUB_TYPES:
            self.display_cbs[t].SetValue(1)

        # Bindings of events
        self.Bind(wx.EVT_MENU, self.OnOpen, self.open)
        self.Bind(wx.EVT_MENU, self.OnClose, self.quit)
        self.Bind(wx.EVT_MENU, self.SelectNone, self.select_none)
        self.Bind(wx.EVT_MENU, self.ImportanceGraph, self.importance)
        self.Bind(wx.EVT_MENU, self.CoverageTable, self.coverage)
        self.Bind(wx.EVT_MENU, self.LargestClubs, self.largest_clubs)
        self.Bind(wx.EVT_MENU, self.ClubNumber, self.number_clubs)
        self.Bind(wx.EVT_MENU, self.OnThresholdChange, self.change_threshold)
        self.Bind(wx.EVT_MENU, self.OnCheckbox, self.view_nontrivials)
        self.Bind(wx.EVT_CHECKLISTBOX, self.OnNodeSelect, self.clb_nodes)
        #self.Bind( wx.EVT_LIST_ITEM_ACTIVATED, self.OnNodeSelect, self.clb_nodes )
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged, self.notebook_BN)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckbox)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)

    def __do_layout(self):

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.vbox.AddSpacer(10)
        self.panel_vis.SetSizer(self.vbox)

        sizer_all = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_club_display = wx.BoxSizer(wx.VERTICAL)
        sizer_cb = wx.GridSizer(2, 2, 0, 0)

        self.sizer_n_staticbox.Lower()
        self.sizer_b_staticbox.Lower()
        sizer_n = wx.StaticBoxSizer(self.sizer_n_staticbox, wx.VERTICAL)
        sizer_b = wx.StaticBoxSizer(self.sizer_b_staticbox, wx.HORIZONTAL)

        sizer_n.Add(self.clb_nodes, 1, wx.EXPAND, 0)
        sizer_b.Add(self.lb_boroughs, 1, wx.EXPAND, 0)
        self.panel_nodes.SetSizer(sizer_n)
        self.panel_boroughs.SetSizer(sizer_b)

        self.notebook_BN.AddPage(self.panel_all, 'All')
        self.notebook_BN.AddPage(self.panel_nodes, 'Nodes')
        self.notebook_BN.AddPage(self.panel_boroughs, 'Boroughs')

        sizer_club_display.Add(self.lc_clubs, 1, wx.EXPAND, 0)

        for t in CLUB_TYPES:
            sizer_cb.Add(self.display_cbs[t], 0, 0, 0)

        sizer_club_display.Add(sizer_cb, 0, wx.EXPAND, 0)
        self.panel_club_display.SetSizer(sizer_club_display)
        self.window_club_display.SetSplitMode(wx.SPLIT_VERTICAL)
        self.window_club_display.SplitVertically(self.panel_club_display, self.nb_club_info, 256) #, 524)

        self.nb_club_info.AddPage(self.tc_club_info, 'Nodes')
        self.nb_club_info.AddPage(self.panel_vis, 'Visualisation')
        self.nb_club_info.AddPage(self.panel_diff, 'Compare')


        self.nb_clubs.AddPage(self.window_club_display, '2-Clubs')

        sizer_3.Add(self.nb_clubs, 1, wx.EXPAND, 0)
        self.window_all_pane_2.SetSizer(sizer_3)
        self.window_all.SplitVertically(self.notebook_BN, self.window_all_pane_2, 196)
        sizer_all.Add(self.window_all, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_all)
        sizer_all.Fit(self)
        self.Layout()
        self.window_club_display.SetSashPosition(256)

    def OnClose(self, e):
        self.Close(True)

    def OnOpen(self, e):
        '''Open a file'''
        dirname = ''
        dlg = wx.FileDialog(self, 'Choose a file', dirname, '', '*.result', wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()

            print dirname
            print filename

            # Clear everything
            self.all_info = dict()
            self.clb_nodes.Clear()
            self.panel_diff.Clear()
            self.tc_club_info.Clear()
            self.axes.clear()
            self.canvas.draw()

            f = open(os.path.join(dirname, filename), 'r')
            self.all_info = pickle.load(f)
            f.close()

            self.panel_diff.SetData(self.all_info)
            self.clb_nodes.AppendItems(self.all_info['nodes'])

            self.nt_threshold = 2.0 * self.all_info['graph'].number_of_edges() / self.all_info['graph'].number_of_nodes()

            self.DisplayAll()

        dlg.Destroy()

    def OnNodeSelect(self, e):
        clb = e.GetEventObject()
        nodes = list(clb.GetCheckedStrings())

        clubs = None

        for node in nodes:
            my_clubs = self.all_info['search'][node]
            if clubs == None:
                clubs = set(my_clubs)
            else:
                clubs &= set(my_clubs)

        for t in CLUB_TYPES:
            self.display_clubs[t] = []

        if clubs != None:
            for club_id in clubs:
                self.display_clubs[self.all_info['club_types'][club_id]].append(str(club_id))

        self.OnClubsChange()
        print ' '


    def OnClubsChange(self):
        '''
        Changes the contents of the list control, according to the selected clubs.
        '''
        data_dict = dict()
        for t in CLUB_TYPES:
            if self.display_cbs[t].Get3StateValue() == wx.CHK_CHECKED:
                for club_id in self.display_clubs[t]:
                    size = len(self.all_info['all_clubs'][int( club_id )])
                    if self.view_nontrivials.IsChecked() or size >= self.nt_threshold:
                        data_dict[int(club_id)] = [club_id, str(size), t]
        self.lc_clubs.ChangeData(data_dict)
        self.panel_diff.Clear()

    def OnCheckbox(self, e):
        self.OnClubsChange()

    def OnItemSelected(self, e):
        item = e.m_itemIndex
        club_id = self.lc_clubs.list_ctrl.GetItemText(item)

        self.tc_club_info.Clear()
        self.club_contents = []
        for node in self.all_info['all_clubs'][int(club_id)]:
            self.club_contents.append(self.all_info['nodes'][node])
            self.tc_club_info.AppendText('%s\n' % self.all_info['nodes'][node])
        self.DrawClub(int(club_id))
        self.panel_diff.ChangeClub(club_id)

    def SelectNone(self,e=None):
        for item in self.clb_nodes.Checked:
            self.clb_nodes.Check(item, check = False)
        self.clb_nodes.DeselectAll()
        self.club_contents = []

    def DisplayAll(self):
        # Display all 2-clubs
        if self.all_info:
            for t in CLUB_TYPES:
                self.display_clubs[t] = []

                for club_id in self.all_info['all_clubs']:
                    t = self.all_info['club_types'][club_id]
                    self.display_clubs[t].append(str(club_id))
            self.OnClubsChange()

    def OnPageChanged(self, e):
        self.SelectNone()
        if e.GetSelection() == 0:
            self.DisplayAll()

    def OnThresholdChange(self, e):

        avg_degree = 2.0 * self.all_info['graph'].number_of_edges() / self.all_info['graph'].number_of_nodes()

        dlg = wx.TextEntryDialog(None, 'Enter the nontrivial-threshold. A 2-club that consists of at least of that number of nodes, is considered nontrivial.', "NonTrivial Threshold", str(avg_degree))

        answer = dlg.ShowModal()

        if answer == wx.ID_OK:
            self.nt_threshold = float(dlg.GetValue())
        else:
            # Default is average degree
            self.nt_threshold = avg_degree

        dlg.Destroy()
        self.OnClubsChange()

    def DrawClub(self, club_id):
        '''
        Draws the selected 2-club in the graph window.

        Parameters
        ----------
        club_id : int
            The id of the 2-club to draw.
        '''

        data = self.all_info
        self.axes.clear()
        if data:
            H = nx.subgraph(data['graph'], self.club_contents)
            pos = nx.spring_layout(H)
            nx.draw(H, pos, self.axes, node_color = 'white', node_size = 200)
            club_type = self.all_info['club_types'][club_id]
            size = len(self.club_contents)
            if club_type in ['Coterie', 'ns-Coterie']:
                # Find centers
                nodelist = [node for node in H.nodes() if len(nx.neighbors(H, node)) == (size - 1)]
                nx.draw_networkx_nodes(H, pos, nodelist, 300, 'gray')
            elif club_type == 'Social circle':
                # Determine central pairs (in a primitive way)
                central_nodes = set()
                central_edges = []
                for i, node1 in enumerate(H.nodes()):
                    ego1 = set(nx.neighbors(H, node1))
                    for node2 in H.nodes()[i:]:
                        ego2 = set(nx.neighbors(H, node2))

                        if len(ego1 | ego2) == size:
                            central_nodes.add(node1)
                            central_nodes.add(node2)
                            central_edges.append((node1,node2))

                nx.draw_networkx_nodes(H, pos, central_nodes, 300, 'gray')
                nx.draw_networkx_edges(H, pos, edgelist = central_edges, width = 8.0, alpha = 0.5, edge_color = 'gray')
            self.canvas.draw()

    def ImportanceGraph(self, e):
        '''
        Draws the importance graph.
        '''
        data = self.all_info
        colors = [len(data['search'][node]) for node in data['nodes']]

        frame = plt.gca()
        frame.set_title('Importance Graph')

        frame.get_xaxis().set_visible(False)
        frame.get_yaxis().set_visible(False)

        nx.draw_networkx(data['graph'], ax = frame, node_color = colors, vmin = min(colors), vmax = max(colors), cmap = plt.cm.autumn)
        plt.colorbar(ax=frame, ticks = [min(colors),max(colors)])

        plt.show()

    def CoverageTable(self, e):
        coverage = dict()
        nt_coverage = dict()
        nt_threshold = self.nt_threshold

        for club_type in CLUB_TYPES:
            coverage[club_type] = set()
            nt_coverage[club_type] = set()

        for c_id, c_items in self.all_info['all_clubs'].items():
            c_type = self.all_info['club_types'][c_id]
            coverage[c_type] = coverage[c_type] | set(c_items)

            if len(c_items) >= nt_threshold:
                nt_coverage[c_type] = nt_coverage[c_type] | set(c_items)


        f = wx.Frame(self,-1)
        f.SetTitle('Coverage table')

        data = [['Club type', 'Coverage', 'Nontrivial Coverage']]

        total_len = len(self.all_info['nodes'])
        for club_type in CLUB_TYPES:
            data.append([club_type, len(coverage[club_type]) / float(total_len), len(nt_coverage[club_type]) / float(total_len)])

        data.append(['All Coteries', len(coverage['Coterie'] | coverage['ns-Coterie']) / float(total_len),
                     len(nt_coverage['Coterie'] | nt_coverage['ns-Coterie']) / float(total_len)])

        grid = ClubGrid(f, data)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND, 0)
        f.SetSizerAndFit(sizer)
        f.Layout()
        f.Show(True)

    def LargestClubs(self, e):
        f = wx.Frame(self,-1)
        f.SetTitle('Maximum degrees')

        data = [['Club type', 'Largest Size', 'Maximum degree']]

        largest = dict()
        for club_type in CLUB_TYPES:
            largest[club_type] = []

        for c_id, c_items in self.all_info['all_clubs'].items():
            my_type = self.all_info['club_types'][c_id]
            if len(c_items) > len(largest[my_type]):
                largest[my_type] = c_items

        G = self.all_info['graph']
        for club_type, club in largest.items():
            H = G.subgraph([self.all_info['nodes'][i] for i in club])

            max_deg = 0
            for node, d in H.degree_iter():
                if d > max_deg:
                    max_deg = d

            data.append([club_type, len(club), max_deg])

        grid = ClubGrid(f, data)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND, 0)
        f.SetSizerAndFit(sizer)
        f.Layout()
        f.Show(True)

    def ClubNumber(self, e):
        f = wx.Frame(self,-1)
        f.SetTitle('Statistics per type')

        number = dict()
        nt_number = dict()

        nt_threshold = self.nt_threshold

        for club_type in CLUB_TYPES:
            number[club_type] = 0
            nt_number[club_type] = 0

        for c_id, c_items in self.all_info['all_clubs'].items():
            my_type = self.all_info['club_types'][c_id]
            number[my_type] += 1

            if len(c_items) >= nt_threshold:
                nt_number[my_type] += 1

        data = [['Club type', 'Number', 'Nontrivial Number']]

        for club_type in CLUB_TYPES:
            data.append([club_type, number[club_type], nt_number[club_type]])
        grid = ClubGrid(f, data)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(grid, 1, wx.EXPAND, 0)
        f.SetSizerAndFit(sizer)
        f.Layout()
        f.Show(True)
# end of class TwoClubViewer

class CheckListCtrl( wx.ListCtrl, listmix.CheckListCtrlMixin ):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1, style = wx.LC_REPORT)
        listmix.CheckListCtrlMixin.__init__( self )
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

    def OnItemActivated(self, evt):
        self.ToggleItem(evt.m_itemIndex)
        evt.Skip()

    def OnCheckItem(self, index, flag):
        if flag:
            what = "checked"
        else:
            what = "unchecked"
        print 'item at index %d was %s\n' % ( index, what )

class CheckListPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.list = CheckListCtrl(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.list.InsertColumn(0, "Node")
        self.list.InsertColumn(1, "Degree")

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.list)

    def OnChangeData(self, items):
        self.list_ctrl.ClearAll()

        self.list_ctrl.InsertColumn(0, 'Node')
        self.list_ctrl.InsertColumn(1, 'Degree')

        for key, data in items.iteritems():
            index = self.list.InsertStringItem(sys.maxint, data[0])
            self.list.SetStringItem(index, 1, data[1])
            self.list.SetItemData(index, key)

    def OnItemSelected(self, evt):
        print 'item selected: %s\n' % evt.m_itemIndex

    def OnItemDeselected(self, evt):
        print 'item deselected: %s\n' % evt.m_itemIndex


class ClubListCtrlPanel(wx.Panel, listmix.ColumnSorterMixin):

    #----------------------------------------------------------------------
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, )#style=wx.WANTS_CHARS)
        self.index = 0

        self.list_ctrl = wx.ListCtrl(self, size = (-1,100), style = wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_SORT_ASCENDING )

        self.list_ctrl.InsertColumn(0, 'ID')
        self.list_ctrl.InsertColumn(1, 'Size')
        self.list_ctrl.InsertColumn(2, 'Type')

        self.item_index = 0
        self.prevColumn = -1
        self.itemDataMap = dict()
        listmix.ColumnSorterMixin.__init__(self, 3)

        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list_ctrl)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1,wx.EXPAND)
        self.SetSizer(sizer)

    def GetColumnSorter(self):
        return self.NumberAndStringSorter

    def GetListCtrl(self):
        return self.list_ctrl

    def OnColClick(self, e):
        e.Skip()

    def NumberAndStringSorter(self, node1, node2):
        #print 'args:', item1, item2

        col = self._col
        ascending = self._colSortFlag[col]

        item1 = self.itemDataMap[node1][self._col]
        item2 = self.itemDataMap[node2][self._col]
        cmpval = 0
        try:
            cmpval = cmp(int(item1), int(item2))
        except ValueError:
            cmpval = cmp(item1, item2)

        if ascending:
            return cmpval
        else:
            return -cmpval

    def ChangeData(self, data_dict):
        self.list_ctrl.ClearAll()

        self.list_ctrl.InsertColumn(0, 'ID')
        self.list_ctrl.InsertColumn(1, 'Size')
        self.list_ctrl.InsertColumn(2, 'Type')

        self.itemDataMap = data_dict

        for key, data in data_dict.items():
            index = self.list_ctrl.InsertStringItem(sys.maxint, data[0])
            self.list_ctrl.SetStringItem(index, 1, data[1])
            self.list_ctrl.SetStringItem(index, 2, data[2])
            self.list_ctrl.SetItemData(index, key)

#---------------------------------------------------------------------------
class ClubGrid(gridlib.Grid): ##, mixins.GridAutoEditMixin):
    def __init__(self, parent, data):
        gridlib.Grid.__init__(self, parent, -1)
        self.moveTo = None
        self.CreateGrid(len(data) - 1, len(data[0]))#, gridlib.Grid.SelectRows)
        self.EnableEditing(False)

        for i, row in enumerate(data):
            for j, value in enumerate(row):
                if i == 0:
                    self.SetColLabelValue(j, str(value))
                else:
                    self.SetCellValue(i-1, j, str(value))

        self.SetRowLabelSize(0)
        self.SetColLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_BOTTOM)

class DiffPanel(wx.Panel):
    def __init__(self, *args, **kwds):
        wx.Panel.__init__(self, *args, **kwds)

        self.panel_left = wx.Panel(self, wx.ID_ANY)
        self.label_left = wx.StaticText(self.panel_left, wx.ID_ANY, "Club ID 1:")
        self.text_common_left = wx.TextCtrl(self.panel_left, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        self.sizer_4_staticbox = wx.StaticBox(self.panel_left, wx.ID_ANY, "Common Nodes")
        self.text_different_left = wx.TextCtrl(self.panel_left, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        self.sizer_5_staticbox = wx.StaticBox(self.panel_left, wx.ID_ANY, "Different Nodes")
        self.panel_right = wx.Panel(self, wx.ID_ANY)
        self.label_right = wx.StaticText(self.panel_right, wx.ID_ANY, "Club ID 2:")
        self.text_club = wx.TextCtrl(self.panel_right, wx.ID_ANY, "")
        self.button = wx.Button(self.panel_right, wx.ID_ANY, "Compare")
        self.text_common_right = wx.TextCtrl(self.panel_right, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        self.sizer_8_staticbox = wx.StaticBox(self.panel_right, wx.ID_ANY, "Common Nodes")
        self.text_different_right = wx.TextCtrl(self.panel_right, wx.ID_ANY, "", style=wx.TE_MULTILINE)
        self.sizer_9_staticbox = wx.StaticBox(self.panel_right, wx.ID_ANY, "Different Nodes")

        sizer_1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_6 = wx.BoxSizer(wx.VERTICAL)
        self.sizer_9_staticbox.Lower()
        sizer_9 = wx.StaticBoxSizer(self.sizer_9_staticbox, wx.HORIZONTAL)
        self.sizer_8_staticbox.Lower()
        sizer_8 = wx.StaticBoxSizer(self.sizer_8_staticbox, wx.HORIZONTAL)
        sizer_7 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        self.sizer_5_staticbox.Lower()
        sizer_5 = wx.StaticBoxSizer(self.sizer_5_staticbox, wx.HORIZONTAL)
        self.sizer_4_staticbox.Lower()
        sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3.Add(self.label_left, 0, 0, 0)
        sizer_3.Add((1, 25), 0, 0, 0)
        sizer_2.Add(sizer_3, 0, wx.EXPAND, 0)
        sizer_4.Add(self.text_common_left, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_4, 1, wx.EXPAND, 0)
        sizer_5.Add(self.text_different_left, 1, wx.EXPAND, 0)
        sizer_2.Add(sizer_5, 1, wx.EXPAND, 0)
        self.panel_left.SetSizer(sizer_2)
        sizer_1.Add(self.panel_left, 1, wx.EXPAND, 0)
        sizer_7.Add(self.label_right, 0, 0, 0)
        sizer_7.Add((1, 25), 0, 0, 0)
        sizer_7.Add(self.text_club, 0, 0, 0)
        sizer_7.Add(self.button, 0, 0, 0)
        sizer_6.Add(sizer_7, 0, wx.EXPAND, 0)
        sizer_8.Add(self.text_common_right, 1, wx.EXPAND, 0)
        sizer_6.Add(sizer_8, 1, wx.EXPAND, 0)
        sizer_9.Add(self.text_different_right, 1, wx.EXPAND, 0)
        sizer_6.Add(sizer_9, 1, wx.EXPAND, 0)
        self.panel_right.SetSizer(sizer_6)
        sizer_1.Add(self.panel_right, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        sizer_1.Fit(self)
        self.Layout()

        self.club = None

        self.Bind(wx.EVT_BUTTON, self.OnSearch, self.button)

    def OnSearch(self, e):
        # Search for the specified ID
        try:
            c_id = int(self.text_club.GetLabelText())
            other_club = set(self.all_info['all_clubs'][c_id])

            all_members = other_club | self.club
            self.text_common_left.Clear()
            self.text_common_right.Clear()
            self.text_different_left.Clear()
            self.text_different_right.Clear()

            for member in all_members:
                node = self.all_info['nodes'][member]
                if member in self.club:
                    if member in other_club:
                        self.text_common_left.AppendText(node)
                        self.text_common_left.AppendText('\n')

                        self.text_common_right.AppendText(node)
                        self.text_common_right.AppendText('\n')

                    else:
                        self.text_different_left.AppendText(node)
                        self.text_different_left.AppendText('\n')

                else:
                    self.text_different_right.AppendText(node)
                    self.text_different_right.AppendText('\n')
        except:
            # No number was entered
            pass

    def SetData(self, data):
        self.all_info = data

    def Clear(self):
        self.text_common_left.Clear()
        self.text_common_right.Clear()
        self.text_different_left.Clear()
        self.text_different_right.Clear()
        self.label_left.SetLabel('Club ID 1:')

    def ChangeClub(self, club_id):
        self.Clear()
        self.label_left.SetLabel('Club ID 1: %d' % (int(club_id),))
        self.club = set(self.all_info['all_clubs'][int(club_id)])

if __name__ == '__main__':
    app = wx.PySimpleApp(0)
    wx.InitAllImageHandlers()
    a = TwoClubViewer(None, -1, '')
    app.SetTopWindow(a)
    a.Show()
    app.MainLoop()
