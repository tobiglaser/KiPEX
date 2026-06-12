import wx
import wx.grid

from z_mat import Z_mat
from engineering_notation import EngUnit
from math import isnan


class ResultsPanel(wx.Panel):
    def __init__(self, parent:wx.Window) -> None:
        super().__init__(parent)

        self.lb = wx.Listbook(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.lb, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.splitters: list[wx.SplitterWindow] = []
        self.nan_warning_shown = False

        if wx.SystemSettings.GetAppearance().IsDark():
            self.off_color_res = wx.Colour(105, 105, 105)
            self.off_color_ind = wx.Colour(173, 173, 173)
        else:
            self.off_color_res = wx.Colour(150, 150, 150)
            self.off_color_ind = wx.Colour(82, 82, 82)

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
            panel = wx.Panel(self.lb)
            self.lb.AddPage(panel, f"{EngUnit(freq, 0,0,'Hz')}")
            bs = wx.BoxSizer()
            splitter = wx.SplitterWindow(panel, style=wx.SP_3D | wx.SP_THIN_SASH | wx.SP_NO_XP_THEME | wx.SP_LIVE_UPDATE)
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
                    if not isnan(res):
                        res_t.SetCellValue(j, k, str(EngUnit(res, 3, 0, 'Ω')))
                    else:
                        res_t.SetCellValue(j, k, "NaN")
                    res_t.SetCellAlignment(j, k, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                    if not j == k:
                        res_t.SetCellTextColour(j, k, self.off_color_res)
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
                    if not isnan(ind): # older EngUnit can not handle NaN implicitly
                        ind_t.SetCellValue(j, k, str(EngUnit(ind, 3, 0, 'H')))
                    else:
                        ind_t.SetCellValue(j, k, "NaN")
                    ind_t.SetCellAlignment(j, k, wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
                    if not j == k:
                        ind_t.SetCellTextColour(j, k, self.off_color_ind)
                    ind_t.SetReadOnly(j, k)
            ind_t.AutoSize()
            ind_t.SetMinSize(wx.Size(0,0))
            l_tables.append(ind_t)
            splitter.SplitVertically(res_t, ind_t)
            panel.SetSizer(bs)
            panel.Fit()
            panel.Layout()
        if z.has_nan() and not self.nan_warning_shown:
            self.nan_warning_shown = True
            wx.CallAfter(
                wx.MessageBox,
                "NaN Results are most likely a result of an open loop.",
                "Warning",
                wx.OK | wx.ICON_WARNING
            )

        def autosize_row_labels(grid: wx.grid.Grid):
            dc = wx.ClientDC(grid)
            dc.SetFont(grid.GetLabelFont())
            max_width = 0
            for row in range(grid.GetNumberRows()):
                label = grid.GetRowLabelValue(row)
                width, _ = dc.GetTextExtent(label)
                if width > max_width:
                    max_width = width
            grid.SetRowLabelSize(max_width + 20)

        def maxize_tables(tables: list[wx.grid.Grid]) -> None:
            col_maxes = []
            for table in tables:
                autosize_row_labels(table)
                col_sizes = [table.GetColSize(i) for i in range(table.GetNumberCols())]
                if not col_maxes:
                    col_maxes = col_sizes
                for i, col in enumerate(col_sizes):
                    table.AutoSizeRowLabelSize(i)
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
        for splitter in self.splitters:
            splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.on_splitter)

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

