import wx



class PortPanel(wx.Panel):
    def __init__(self, parent: wx.Window, text: str = "", components: dict[str, list[str]] = {}) -> None:
        super().__init__(parent)
        self.components = components
        border = wx.StaticBoxSizer(wx.HORIZONTAL, self, text)
        self.SetSizer(border)

        
        #border.Add(start_box, 0, wx.ALL | wx.EXPAND, 5)
        fgs = wx.FlexGridSizer(3)
        border.Add(fgs, 1, wx.EXPAND)
        fgs.AddGrowableCol(0, 1)
        fgs.AddGrowableCol(2, 1)
        fgs.Add(wx.StaticText(self, label="Component"), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        fgs.AddSpacer(5)
        fgs.Add(wx.StaticText(self, label="Pin"), 1, wx.ALIGN_CENTER | wx.TOP | wx.RIGHT, 5)
        self.component_box = wx.ComboBox(self, style=wx.CB_READONLY, choices=list(components.keys()))
        self.component_box.Bind(wx.EVT_COMBOBOX, self.on_component_select)
        fgs.Add(self.component_box, 1, wx.EXPAND | wx.TOP | wx.LEFT | wx.BOTTOM, 5)
        fgs.AddSpacer(5)
        self.pin_box = wx.ComboBox(self, style=wx.CB_READONLY, value="")
        self.pin_box.Disable()
        fgs.Add(self.pin_box, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM, 5)

    def on_component_select(self, event: wx.Event):
        self.pin_box.Enable()
        component = self.component_box.GetStringSelection()
        #pin = self.pin_box.GetValue()
        self.pin_box.SetItems(self.components[component])
        #if pin in self.components[component]:
        #    self.pin_box.SetStringSelection(pin)
        #else:
        #    self.pin_box.SetSelection(0)








if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    #sw = wx.ScrolledWindow(frame)
    sw = wx.Panel(frame)
    bs = wx.BoxSizer(wx.VERTICAL)
    sw.SetSizer(bs)
    p1 = PortPanel(sw, "Source", {"A": ["a", "aa", "aaa"], "B": ["b", "bb", "bbb"]})
    p2 = PortPanel(sw, "Sink", {"A": ["a", "aa", "aaa"], "B": ["b", "a", "bb", "bbb"]})
    bs.Add(p1, 0, wx.ALL | wx.EXPAND, 5)
    bs.Add(p2, 0, wx.ALL | wx.EXPAND, 5)

    frame.Show()
    app.MainLoop()