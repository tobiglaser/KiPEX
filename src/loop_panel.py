import wx
from loop_list import LoopList


class LoopPanel(wx.ScrolledWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent, style=wx.HSCROLL)
        self.SetScrollRate(10, 0)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        self.loop_lists: list[LoopList] = []
        ll1 = LoopList(self, "Loop 1")
        self.loop_lists.append(ll1)
        self.sizer.Add(ll1, 0, wx.EXPAND | wx.ALL, 10)
        self.add_button = wx.Button(self, label="➕")
        self.sizer.Add(self.add_button, 0, wx.EXPAND | wx.ALL, 10)
        self.add_button.Bind(wx.EVT_BUTTON, self.on_add)
        ll1.close_button.Bind(wx.EVT_BUTTON, self.on_loop_close)
        
    def on_add(self, event: wx.Event) -> None:
        loop_number = len(self.loop_lists)
        ll = LoopList(self, f"Loop {loop_number + 1}")
        ll.close_button.Bind(wx.EVT_BUTTON, self.on_loop_close)
        self.loop_lists.append(ll)
        self.sizer.Insert(loop_number, ll, 0, wx.EXPAND | wx.ALL, 10)
        self.FitInside()
        self.Layout()
        wx.CallAfter(self.Scroll, self.GetScrollRange(wx.HORIZONTAL), -1)

    def on_loop_close(self, event: wx.Event) -> None:
        source = event.GetEventObject()
        for ll in self.loop_lists:
            if source == ll.close_button:
                self.loop_lists.remove(ll)
                self.sizer.Detach(ll)
                ll.Destroy()
                break
        self.FitInside()
        self.Layout()



if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    LoopPanel(frame)
    frame.Show()
    app.MainLoop()