import wx
import wx.grid
import wx.lib.agw.aui as aui
import wx.lib.agw.flatnotebook as fnb

from z_mat import Z_mat
from engineering_notation import EngUnit
from typing import List


class ResultsPanel(wx.Panel):
    def __init__(self, parent:wx.Window) -> None:
        super().__init__(parent)

        self.lb = wx.Listbook(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.lb, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.splitters: List[wx.SplitterWindow] = []
        #self.read()

    def read(self, csv: str = "Zc.csv", mat: str = "Zc.mat") -> None:
        self.lb.DeleteAllPages()
        self.splitters.clear()
        r_tables = []
        l_tables = []
        
        z = Z_mat(csv, mat)
        F = z.GetFrequencies()
        L = z.GetInductance()
        R = z.GetResistance()
        P = z.GetRowPortNames()

        for i, freq in enumerate(F):
            panel = wx.Panel(self)
            self.lb.AddPage(panel, f"{EngUnit(freq, 0,0,'Hz')}")
            bs = wx.BoxSizer()
            splitter = wx.SplitterWindow(panel)
            bs.Add(splitter, 1, wx.EXPAND)
            self.splitters.append(splitter)
            splitter.SetSashGravity(0.5)
            splitter.SetMinimumPaneSize(100)
            
            res_t = wx.grid.Grid(splitter)
            res_t.CreateGrid(len(P), len(P))
            for j, port in enumerate(P):
                res_t.SetColLabelValue(j, port)
                res_t.SetRowLabelValue(j, port)
            for j, row in enumerate(R[i]):
                for k, res in enumerate(row):
                    res_t.SetCellValue(j, k, str(EngUnit(res, 3, 0, 'Ω')))
                    res_t.SetCellAlignment(j, k, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                    if not j == k:
                        res_t.SetCellTextColour(j, k, wx.Colour(105, 105, 105))
                    res_t.SetReadOnly(j, k)
            res_t.AutoSize()
            res_t.SetMinSize(wx.Size(0,0))
            r_tables.append(res_t)

            ind_t = wx.grid.Grid(splitter)
            ind_t.CreateGrid(len(P), len(P))
            for j, port in enumerate(P):
                ind_t.SetColLabelValue(j, port)
                ind_t.SetRowLabelValue(j, port)
            for j, row in enumerate(L[i]):
                for k, ind in enumerate(row):
                    ind_t.SetCellValue(j, k, str(EngUnit(ind, 3, 0, 'H')))
                    ind_t.SetCellAlignment(j, k, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                    if not j == k:
                        ind_t.SetCellTextColour(j, k, wx.Colour(173, 173, 173))
                    ind_t.SetReadOnly(j, k)
            ind_t.AutoSize()
            ind_t.SetMinSize(wx.Size(0,0))
            l_tables.append(ind_t)
            width = panel.GetSize().GetWidth()
            splitter.Initialize(res_t)
            splitter.SplitVertically(res_t, ind_t, width // 2)
            for splitter in self.splitters:
                splitter.SetSashPosition(width//2)
            print(width, splitter.GetWindow1().GetSize().GetWidth(), splitter.GetWindow1().GetSize().GetWidth(), splitter.GetSashPosition(), [s.GetSashPosition() for s in self.splitters])
            panel.SetSizer(bs)
            panel.Fit()
            panel.Layout()
        
        def maxize_tables(tables: List[wx.grid.Grid]) -> None:
            col_maxes = []
            for table in tables:
                #for i in range(table.GetNumberCols()):
                col_sizes = [table.GetColSize(i) for i in range(table.GetNumberCols())]
                if not col_maxes:
                    col_maxes = col_sizes
                for i, col in enumerate(col_sizes):
                    if col > col_maxes[i]:
                        col_maxes[i] = col
            for table in tables:
                for i, size in enumerate(col_maxes):
                    table.SetColSize(i, size)
                for row in range(table.GetNumberRows()):
                    table.DisableRowResize(row)
                for col in range(table.GetNumberRows()):
                    table.DisableColResize(col)

        maxize_tables([*r_tables, *l_tables])
        self.Fit()
        for table in r_tables:
            table.SetMinSize(table.GetSize())
        for table in l_tables:
            table.SetMinSize(table.GetSize())
        #!for splitter in self.splitters:
        #!    splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_splitter)

    def on_splitter(self, event: wx.SplitterEvent) -> None:
        pos = event.GetSashPosition()
        for splitter in self.splitters:
            splitter.SetSashPosition(pos)



if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    panel = ResultsPanel(frame)
    panel.read()
    frame.Fit()
    frame.Show()
    app.MainLoop()

