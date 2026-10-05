import wx



class SubPanel(wx.Panel):
    def __init__(self, parent: wx.Window, text: str = "", choices: list[str] = [], second_choices: dict[str, list[str]] = {}) -> None:
        super().__init__(parent)
        border = wx.StaticBoxSizer(wx.HORIZONTAL, self, text)
        self.SetSizer(border)
        self.combobox = wx.ComboBox(self, style=wx.CB_READONLY, value="", choices=choices)
        border.Add(self.combobox, 1, wx.ALL | wx.EXPAND, 5)
        self.second_coices = second_choices

        self.combobox2 = None
        if second_choices:
            self.combobox2 = wx.ComboBox(self, style=wx.CB_READONLY, value="")
            self.combobox.Bind(wx.EVT_COMBOBOX, self.on_component_select)
            self.combobox2.Disable()
            #if len(second_choices) == 1:
            #    self.combobox2.SetValue(second_choices[0])
            border.Add(self.combobox2, 1, wx.ALL | wx.EXPAND, 5)
        
        self.close_button = wx.BitmapButton.NewCloseButton(self, self.Id)
        border.Add(self.close_button, 0, wx.ALL | wx.EXPAND, 5)

    def on_component_select(self, event: wx.Event):
        if not self.combobox2: return
        self.combobox2.Enable()
        component = self.combobox.GetStringSelection()
        self.combobox2.SetItems(self.second_coices[component])
        self.combobox2.SetValue("")
        event.Skip()





if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    #sw = wx.ScrolledWindow(frame)
    sw = wx.Panel(frame)
    bs = wx.BoxSizer(wx.VERTICAL)
    sw.SetSizer(bs)
    p1 = SubPanel(sw, "Net", ["Z", "Y", "X"])
    bs.Add(p1, 0, wx.ALL | wx.EXPAND, 5)
    p2 = SubPanel(sw, "Net", ["Z", "Y", "X"], {"X": ["1"], "Y": ["1", "2"], "Z": ["1", "2", "3"]})
    bs.Add(p2, 0, wx.ALL | wx.EXPAND, 5)

    frame.Show()
    app.MainLoop()