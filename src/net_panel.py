import wx
from typing import Any
def emptycb(event: wx.Event):
    print("placeholder")

class NetPanel(wx.Panel):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent=parent)
        self.net_list = wx.ListBox(self, choices=[], style=wx.LB_MULTIPLE)
        all_button = wx.Button(self, label="All")
        all_button.Bind(wx.EVT_BUTTON, self.on_all)
        none_button = wx.Button(self, label="None")
        none_button.Bind(wx.EVT_BUTTON, self.on_none)
        named_button = wx.Button(self, label="Named")
        named_button.Bind(wx.EVT_BUTTON, self.on_named)
        preset_sizer = wx.StaticBoxSizer(orient=wx.HORIZONTAL, parent=self, label="Quick Selection")
        preset_sizer.Add(all_button, 1, wx.LEFT | wx.TOP | wx.BOTTOM, 5)
        preset_sizer.Add(none_button, 1, wx.ALL, 5)
        preset_sizer.Add(named_button, 1, wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
        
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(self.net_list, 1, wx.EXPAND | wx.ALL, 10)
        left_sizer.Add(preset_sizer, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        
        sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Net Selection")
        sizer.Add(left_sizer, 1, wx.EXPAND)
        addsub_sizer = wx.BoxSizer(wx.VERTICAL)
        addsub_sizer.AddStretchSpacer(4)
        right_button = wx.Button(self, label="->")
        right_button.Bind(wx.EVT_BUTTON, self.on_add)
        addsub_sizer.Add(right_button)
        addsub_sizer.AddStretchSpacer(1)
        left_button = wx.Button(self, label="<-")
        left_button.Bind(wx.EVT_BUTTON, self.on_remove)
        addsub_sizer.Add(left_button)
        addsub_sizer.AddStretchSpacer(4)
        sizer.Add(addsub_sizer, 0, wx.EXPAND)

        self.plot_list = wx.ListBox(self, choices=[], style=wx.LB_SINGLE)
        self.plot_list.Bind(wx.EVT_LISTBOX, self.on_sel_net)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        right_sizer.Add(self.plot_list, 1, wx.EXPAND | wx.ALL, 10)
        ud_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Port Selection")
        
        self.swap_button = wx.Button(self, label="⇆")
        self.swap_button.Bind(wx.EVT_BUTTON, self.on_swap)
        self.swap_button.Disable()
        self.combo_source = wx.ComboBox(self, value="", choices = [])
        self.combo_source.Bind(wx.EVT_COMBOBOX, self.on_port_combo)
        self.combo_source.Disable()
        self.combo_sink = wx.ComboBox(self, value="", choices = [])
        self.combo_sink.Bind(wx.EVT_COMBOBOX, self.on_port_combo)
        self.combo_sink.Disable()
        ud_sizer.Add(self.combo_source, 1, wx.TOP | wx.BOTTOM | wx.LEFT, 5)
        ud_sizer.Add(self.swap_button, 0, wx.ALL, 5)
        ud_sizer.Add(self.combo_sink, 1, wx.TOP | wx.BOTTOM | wx.RIGHT, 5)
        
        right_sizer.Add(ud_sizer, 0, wx.EXPAND | wx.BOTTOM | wx.LEFT | wx.RIGHT, 10)
        sizer.Add(right_sizer, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def set_net_pads(self, net_pad_dict: dict[str, list[str]]) -> None:
        self.np_dict = net_pad_dict
        self.net_list.SetItems([net for net in net_pad_dict.keys()])
        self.portdict = {}
        for net, pads in net_pad_dict.items():
            if len(pads) < 2:
                continue
            self.portdict[net] = {}
            self.portdict[net]["source"] = pads[0]
            self.portdict[net]["sink"] = pads[1]
            pass

    def on_add(self, event: Any) -> None:
        all = self.net_list.GetStrings()
        selections = self.net_list.GetSelections()
        
        new = self.plot_list.GetStrings()
        for item in selections:
            new.append(all[item])
        self.plot_list.Set(new)
        self.plot_list.SetSelection(len(new)-1)
        evt = wx.CommandEvent(wx.EVT_LISTBOX.typeId, self.plot_list.GetId())
        self.plot_list.GetEventHandler().ProcessEvent(evt)
        
        for item in reversed(selections):
            all.remove(all[item])
        self.net_list.Set(all)

    def on_remove(self, event: Any) -> None:
        all = self.plot_list.GetStrings()
        selections = self.plot_list.GetSelections()

        new = self.net_list.GetStrings()
        for item in selections:
            new.append(all[item])
        
        def find_index(layer: str) -> int:
            for i, entry in enumerate(self.np_dict.keys()):
                if entry == layer:
                    return i
            return -1
        new.sort(key=find_index)
        self.net_list.Set(new)
        
        for item in reversed(selections):
            all.remove(all[item])
        self.plot_list.Set(all)

        self.combo_source.Clear()
        self.combo_source.Disable()
        self.combo_sink.Clear()
        self.combo_source.Disable()
        self.swap_button.Disable()

    def on_sel_net(self, event: wx.Event) -> None:
        warn = " ⚠️"
        sel = self.plot_list.GetSelection()
        if sel == -1 : return
        all = self.plot_list.GetStrings()
        net = all[sel].removesuffix(warn)
        port = self.portdict[net]
        self.combo_source.Enable()
        self.combo_source.SetItems(self.np_dict[net])
        self.combo_source.SetValue(port["source"])
        self.combo_sink.Enable()
        self.combo_sink.SetItems(self.np_dict[net])
        self.combo_sink.SetValue(port["sink"])
        self.swap_button.Enable()
        evt = wx.CommandEvent(wx.EVT_COMBOBOX.typeId, self.plot_list.GetId())
        self.plot_list.GetEventHandler().ProcessEvent(evt)

    def on_port_combo(self, event: wx.Event) -> None:
        warn = " ⚠️"
        sel = self.plot_list.GetSelection()
        str = self.plot_list.GetStringSelection()
        source = self.combo_source.Value
        sink = self.combo_sink.Value
        self.portdict[str.removesuffix(warn)]["source"] = source
        self.portdict[str.removesuffix(warn)]["sink"] = sink
        if source == sink and not str.endswith(warn):
            self.plot_list.SetString(sel, f"{str}{warn}")
        else:
            self.plot_list.SetString(sel, str.removesuffix(warn))

    def on_swap(self, event: wx.Event) -> None:
        warn = " ⚠️"
        str = self.plot_list.GetStringSelection()
        source = self.combo_source.Value
        sink = self.combo_sink.Value
        self.combo_source.SetValue(sink)
        self.combo_sink.SetValue(source)

        self.portdict[str.removesuffix(warn)]["source"] = sink
        self.portdict[str.removesuffix(warn)]["sink"] = source

    def on_all(self, event: wx.Event) -> None:
        nets = self.net_list.GetStrings()
        for net in nets:
            self.net_list.SetStringSelection(net)
            self.on_add(None)
    
    def on_none(self, event: wx.Event) -> None:
        nets = self.plot_list.GetStrings()
        for net in nets:
            self.plot_list.SetStringSelection(net)
            self.on_remove(None)

    def on_named(self, event: wx.Event) -> None:
        nets = self.net_list.GetStrings()
        for net in nets:
            if net and not net.startswith("Net-(") and not net.startswith("unconnected-("):
                self.net_list.SetStringSelection(net)
                self.on_add(None)




if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    panel = NetPanel(frame)
    sizer = wx.BoxSizer()
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Fit()
    frame.Show()
    app.MainLoop()