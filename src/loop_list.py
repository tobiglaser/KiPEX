import wx
from port_panel import PortPanel
from sub_panel import SubPanel


class LoopList(wx.Panel):
    def __init__(self, parent: wx.Window, name: str = "", components: dict[str, list[str]] = {}, pin_nets: dict[str, str] = {}) -> None:
        super().__init__(parent)
        self.components = components
        self.pin_nets = pin_nets
        self.subpanels: list[SubPanel] = []
        self.end_net_panel: SubPanel | None = None
        self.used_nets: list[str] = []
        self.border_sizer = wx.StaticBoxSizer(wx.VERTICAL, self)#, label=name)
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.name_field = wx.TextCtrl(self, value=name, style=wx.TE_PROCESS_ENTER)
        #self.name_field.Bind(wx.EVT_TEXT_ENTER, lambda a: self.border_sizer.GetStaticBox().SetLabel(self.name_field.GetValue()))
        #self.name_field.Bind(wx.EVT_KILL_FOCUS, lambda a: self.border_sizer.GetStaticBox().SetLabel(self.name_field.GetValue()))
        name_sizer.Add(self.name_field, 1, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        self.close_button = wx.BitmapButton.NewCloseButton(self, self.Id)
        
        name_sizer.Add(self.close_button, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        self.border_sizer.Add(name_sizer, 0, wx.EXPAND, 0)
        self.SetSizer(self.border_sizer)

        self.scroll = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self.scroll.SetScrollRate(0, 10)
        self.list = wx.BoxSizer(wx.VERTICAL)
        self.scroll.SetSizer(self.list)
        self.border_sizer.Add(self.scroll, 1, wx.EXPAND)
        self.source_panel = PortPanel(self.scroll, "Source", components)
        self.list.Add(self.source_panel, 0, wx.EXPAND | wx.ALL, 5)

        self.list.AddStretchSpacer(1)
        self.sink_panel = PortPanel(self.scroll, "Sink", components)
        self.list.Add(self.sink_panel, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)

        self.source_panel.pin_box.Bind(wx.EVT_COMBOBOX, handler=self.on_pin_selected)
        self.sink_panel.pin_box.Bind(wx.EVT_COMBOBOX, handler=self.on_pin_selected)

    #Dummy for later model
    def components_on_net(self, net: str) -> list[str]:
        return ["A", "B"]
    #Dummy for later model
    def nets_on_component(self, component: str) -> list[str]:
        return ["a", "b"]
    #Dummy for later model
    def mockup_options_for_components(self, components: list[str]) -> dict[str, list[str]]:
        return {"A": ["a", "b"], "B": ["a", "b"]}

    def on_subpanel_close(self, event: wx.Event) -> None:
        source = event.GetEventObject()
        for subpanel in self.subpanels:
            if source == subpanel.close_button:
                value = subpanel.combobox.GetValue()
                if value and not subpanel.combobox2:
                    self.used_nets.remove(value)

                self.subpanels.remove(subpanel)
                self.list.Detach(subpanel)
                subpanel.Destroy()
                if self.subpanels:
                    self.subpanels[-1].Enable()
                    # if the previous panel has no choices, close it as well by internal button click
                    if not self.subpanels[-1].combobox.GetStrings():
                        command_event = wx.CommandEvent(wx.EVT_BUTTON.typeId)
                        command_event.SetEventObject(self.subpanels[-1].close_button)
                        wx.PostEvent(self.subpanels[-1].close_button, command_event)
                else:
                    self.source_panel.Enable()

    def on_pin_selected(self, event: wx.Event) -> None:
        source = event.GetEventObject()
        if source == self.source_panel.pin_box:
            self.source_panel.Disable()
            net = self.pin_nets[f"{self.source_panel.component_box.GetValue()}-{self.source_panel.pin_box.GetValue()}"]
            net_panel = SubPanel(self.scroll, "Net")
            net_panel.combobox.SetValue(net)
            self.used_nets.append(net)
            net_panel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
            net_panel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
            self.subpanels.append(net_panel)
            self.list.Insert(1, net_panel, 0, wx.EXPAND | wx.ALL, 5)
            self.Layout()
            net_panel.Disable()
            components = self.components_on_net(net)
            comp_panel = SubPanel(self.scroll, "Component", components, self.mockup_options_for_components(components))
            comp_panel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
            comp_panel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
            self.subpanels.append(comp_panel)
            self.list.Insert(2, comp_panel , 0, wx.EXPAND | wx.ALL, 5)
            self.Layout()

        elif source == self.sink_panel.pin_box:
            print("STOP")

    def on_sub_selection(self, event: wx.Event) -> None:
        source = event.GetEventObject()

        subpanel = self.subpanels[-1]
        if not source == subpanel.combobox:
            if subpanel.combobox2 and not source == subpanel.combobox2:
                raise
        source_index = -1
        for i, panel in enumerate(self.list.GetChildren()):
            if panel.GetWindow() == subpanel:
                source_index = i
                break

        if not subpanel.combobox2:
            net = subpanel.combobox.GetValue()
            self.used_nets.append(net)

        if subpanel.combobox2:
            if not subpanel.combobox2.GetValue():
                subpanel.combobox2.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
                event.Skip()
                return



        subpanel.Disable()

        new_subpanel = None

        if subpanel.combobox2: # is component
            nets = self.nets_on_component(subpanel.combobox.GetValue())
            for net in self.used_nets:
                if net in nets:
                    nets.remove(net)
            new_subpanel = SubPanel(self.scroll, "Net", nets)
        else:
            components = self.components_on_net(subpanel.combobox.GetValue())
            new_subpanel = SubPanel(self.scroll, "Component", components, self.mockup_options_for_components(components))

        new_subpanel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
        new_subpanel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
        self.subpanels.append(new_subpanel)
        self.list.Insert(source_index + 1, new_subpanel, 0, wx.EXPAND | wx.ALL, 5)
        print(source_index)
        self.Layout()


        #for i, item in enumerate(self.list.GetChildren()):
        #    print(i, item)
            
        
        




if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    sw = wx.Panel(frame)
    bs = wx.BoxSizer(wx.HORIZONTAL)
    sw.SetSizer(bs)
    l = LoopList(sw, "Loop 1", {"A": ["a", "aa", "aaa"], "B": ["b", "bb", "bbb"]}, {"A-aaa": "Z", "A-aa": "Y", "A-a": "X", "B-b": "Z", "B-bb": "Y", "B-bbb": "X"})
    bs.Add(l, 0, wx.ALL | wx.EXPAND, 5)
    frame.Show()
    app.MainLoop()