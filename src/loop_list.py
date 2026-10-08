import wx
from port_panel import PortPanel
from sub_panel import SubPanel
from gui_circuit_model import GuiCircuitModel


class LoopList(wx.Panel):
    def __init__(self, parent: wx.Window, name: str = "") -> None:
        super().__init__(parent)
        gcm = GuiCircuitModel.get_instance()
        self.subpanels: list[SubPanel] = []
        self.used_nets: list[str] = []
        self.end_net  = ""
        self.last_net = ""
        self.closed = False
        self.border_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label=name)
        name_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.name_field = wx.TextCtrl(self, value=name, style=wx.TE_PROCESS_ENTER)
        self.name_field.Bind(wx.EVT_TEXT_ENTER, lambda a: self.border_sizer.GetStaticBox().SetLabel(self.name_field.GetValue()))
        self.name_field.Bind(wx.EVT_KILL_FOCUS, lambda a: self.border_sizer.GetStaticBox().SetLabel(self.name_field.GetValue()))
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
        self.source_panel = PortPanel(self.scroll, "Source", gcm.get_component_pin_dict())
        self.list.Add(self.source_panel, 0, wx.EXPAND | wx.ALL, 5)

        self.list.AddStretchSpacer(1)
        self.sink_panel = PortPanel(self.scroll, "Sink", gcm.get_component_pin_dict())
        self.list.Add(self.sink_panel, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)

        self.source_panel.pin_box.Bind(wx.EVT_COMBOBOX, handler=self.on_pin_selected)
        self.sink_panel.pin_box.Bind(wx.EVT_COMBOBOX, handler=self.on_pin_selected)

        self.completenes_hint = wx.StaticText(self, label="Loop Open ❌")
        self.border_sizer.Add(self.completenes_hint, 0, wx.ALIGN_CENTER | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)

    def on_subpanel_close(self, event: wx.Event) -> None:
        source = event.GetEventObject()
        for subpanel in self.subpanels:
            if source == subpanel.close_button:
                value = subpanel.combobox.GetValue()
                if value and not subpanel.combobox2:
                    self.used_nets.remove(value)
                    self.last_net = ""
                    self.on_last_nets_changed()

                self.subpanels.remove(subpanel)
                self.list.Detach(subpanel)
                subpanel.Destroy()
                if self.subpanels:
                    self.subpanels[-1].Enable()
                    # if the previous panel is not the net panel closing the loop
                    if not self.end_net == self.subpanels[-1].combobox.GetValue():
                        # if the previous panel has no choices, close it as well by internal button click
                        if len(self.subpanels[-1].combobox.GetStrings()) <= 1:
                            command_event = wx.CommandEvent(wx.EVT_BUTTON.typeId)
                            command_event.SetEventObject(self.subpanels[-1].close_button)
                            wx.PostEvent(self.subpanels[-1].close_button, command_event)
                else:
                    self.source_panel.Enable()
                self.Layout()

    def on_pin_selected(self, event: wx.Event) -> None:
        source = event.GetEventObject()
        gcm = GuiCircuitModel.get_instance()
        if source == self.source_panel.pin_box:
            self.source_panel.Disable()
            net = gcm.get_net_of_component_pin(self.source_panel.component_box.GetValue(), self.source_panel.pin_box.GetValue())            
            self.last_net = net
            self.used_nets.append(net)
            self.on_last_nets_changed()

            net_panel = SubPanel(self.scroll, "Net")
            net_panel.combobox.SetItems([net])
            net_panel.combobox.SetValue(net)
            net_panel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
            net_panel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
            self.subpanels.append(net_panel)
            self.list.Insert(1, net_panel, 0, wx.EXPAND | wx.ALL, 5)
            self.Layout()
            if self.closed:
                return
            net_panel.Disable()
            gcm = GuiCircuitModel.get_instance()
            components = gcm.get_components_in_net(net)
            comp_panel = SubPanel(self.scroll, "Component", components, gcm.get_mockup_options_for_components(components))
            comp_panel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
            comp_panel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
            self.subpanels.append(comp_panel)
            self.list.Insert(2, comp_panel , 0, wx.EXPAND | wx.ALL, 5)
            self.Layout()
        elif source == self.sink_panel.pin_box:
            net = gcm.get_net_of_component_pin(self.sink_panel.component_box.GetValue(), self.sink_panel.pin_box.GetValue())
            self.end_net = net
            self.on_last_nets_changed()
            self.sink_panel.set_net(net)
            self.Layout()
            self.scroll.Scroll(-1, self.scroll.GetScrollRange(wx.VERTICAL))


    def on_last_nets_changed(self) -> None:
        if self.last_net == self.end_net and self.last_net:
            self.completenes_hint.SetLabelText("Loop Closed ✅")
            self.closed = True
            if self.subpanels:
                while self.subpanels[-1].combobox.GetValue() != self.end_net:
                    sp = self.subpanels[-1]
                    self.subpanels.remove(sp)
                    self.list.Detach(sp)
                    sp.Destroy()
                    self.subpanels[-1].Enable()
        else:
            self.completenes_hint.SetLabelText("Loop Open ❌")
            self.closed = False


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
            self.last_net = net
            self.on_last_nets_changed()

        if subpanel.combobox2:
            if not subpanel.combobox2.GetValue():
                subpanel.combobox2.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
                event.Skip()
                return

        if self.closed:
            return

        subpanel.Disable()

        new_subpanel = None

        if subpanel.combobox2: # is component
            gcm = GuiCircuitModel.get_instance()
            nets = gcm.get_nets_on_component(subpanel.combobox.GetValue())
            for net in self.used_nets:
                if net in nets:
                    nets.remove(net)
            new_subpanel = SubPanel(self.scroll, "Net", nets)
        else:
            gcm = GuiCircuitModel.get_instance()
            components = gcm.get_components_in_net(subpanel.combobox.GetValue())
            new_subpanel = SubPanel(self.scroll, "Component", components, gcm.get_mockup_options_for_components(components))

        new_subpanel.combobox.Bind(wx.EVT_COMBOBOX, self.on_sub_selection)
        new_subpanel.close_button.Bind(wx.EVT_BUTTON, self.on_subpanel_close)
        self.subpanels.append(new_subpanel)
        self.list.Insert(source_index + 1, new_subpanel, 0, wx.EXPAND | wx.ALL, 5)
        self.Layout()
        self.scroll.Scroll(-1, self.scroll.GetScrollRange(wx.VERTICAL))




if __name__ == "__main__":
    from kipy import KiCad
    GuiCircuitModel.from_KiCad(KiCad().get_board())
    app = wx.App()
    frame = wx.Frame(None)
    sw = wx.Panel(frame)
    bs = wx.BoxSizer(wx.HORIZONTAL)
    sw.SetSizer(bs)
    l = LoopList(sw, "Loop 1")
    bs.Add(l, 0, wx.ALL | wx.EXPAND, 5)
    frame.Show()
    app.MainLoop()