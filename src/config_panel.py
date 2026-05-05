import wx
from fh_config import FHConfigDialog
from typing import Dict, Callable
from engineering_notation import EngUnit

def emptycb(event: wx.Event):
    print("placeholder")
def spincb(event: wx.SpinEvent):
    print("placeholder")

class ConfigPanel(wx.Panel):
    def __init__(self, parent: wx.Window, settings: Dict = {}, fh_callback: Callable = print) -> None:
        super().__init__(parent=parent)
        self.settings = settings
        self.fh_callback = fh_callback
        self.running = False
        sizer = wx.StaticBoxSizer(wx.VERTICAL, self, "Configuration:")
        self.SetSizer(sizer)

        freq_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, "Frequency")
        inner_freq_sizer = wx.FlexGridSizer(5)
        inner_freq_sizer.AddGrowableCol(0, 1)
        inner_freq_sizer.AddGrowableCol(2, 1)
        inner_freq_sizer.AddGrowableCol(4, 1)
        sizer.Add(freq_sizer, 0, wx.EXPAND | wx.ALL, 5)
        freq_sizer.Add(inner_freq_sizer, 1)
        inner_freq_sizer.Add(wx.StaticText(self, label="fmin"), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        inner_freq_sizer.AddStretchSpacer()
        inner_freq_sizer.Add(wx.StaticText(self, label="fmax"), 1, wx.ALIGN_CENTER | wx.TOP, 5)
        inner_freq_sizer.AddStretchSpacer()
        inner_freq_sizer.Add(wx.StaticText(self, label="ndec"), 1, wx.ALIGN_CENTER | wx.TOP | wx.RIGHT, 5)
        min = self.settings.get("freqs", {}).get("str_min", "100m")
        max = self.settings.get("freqs", {}).get("str_max", "100M")
        self.spin1 = wx.TextCtrl(self, style=wx.TE_RIGHT, value=min)
        self.spin2 = wx.TextCtrl(self, style=wx.TE_RIGHT, value=max)
        self.spin2.Bind(wx.EVT_MOUSEWHEEL, lambda a: print("Scroll"))
        self.spin3 = wx.SpinCtrl(self, min = 1, initial=self.settings.get("freqs", {}).get("ndec", 1))
        inner_freq_sizer.Add(self.spin1, 1, wx.EXPAND | wx.TOP | wx.BOTTOM | wx.LEFT, 5)
        inner_freq_sizer.AddSpacer(5)
        inner_freq_sizer.Add(self.spin2, 1, wx.EXPAND | wx.ALL, 5)
        inner_freq_sizer.AddSpacer(5)
        inner_freq_sizer.Add(self.spin3, 1, wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, 5)

        sizer.AddStretchSpacer(1)

        bottom_sizer = wx.FlexGridSizer(2)
        sizer.Add(bottom_sizer, 1, wx.EXPAND)
        bottom_sizer.AddGrowableCol(0, 1)
        bottom_sizer.AddGrowableCol(1, 1)
        bottom_sizer.AddGrowableRow(0, 1)
        bottom_sizer.AddGrowableRow(1, 2)

        fila_button = wx.Button(self, label="Filamentization")
        config_fh_button = wx.Button(self, label="Configure FastHenry")
        gen_button = wx.Button(self, label="Generate .inp only")
        self.run_button = wx.Button(self, label="Start Simulation!")
        bottom_sizer.Add(fila_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(config_fh_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(gen_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(self.run_button, 1, wx.EXPAND | wx.ALL, 5)
        fila_button.Bind(wx.EVT_BUTTON, emptycb)
        fila_button.Disable()
        config_fh_button.Bind(wx.EVT_BUTTON, self.on_config_fh)
        gen_button.Bind(wx.EVT_BUTTON, emptycb)
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_fh)

    def apply_freqs(self) -> None:
        self.settings["freqs"] = {}
        self.settings["freqs"]["str_min"] = self.spin1.GetValue()
        self.settings["freqs"]["min"] = float(EngUnit(self.spin1.GetValue().replace(',', '.'), 3, 0, "Hz"))
        self.settings["freqs"]["str_max"] = self.spin2.GetValue()
        self.settings["freqs"]["max"] = float(EngUnit(self.spin2.GetValue().replace(',', '.'), 3, 0, "Hz"))
        self.settings["freqs"]["ndec"] = self.spin3.GetValue()
    
    def on_config_fh(self, event: wx.Event) -> None:
        dialog = FHConfigDialog(self, self.settings.get("fh_config", {}))
        dialog.ShowModal()
        self.settings["fh_config"] = dialog.config

    def on_filament(self, event: wx.Event) -> None:
        print("Placeholder!")

    def on_run_fh(self, event: wx.Event) -> None:
        if not self.running:
            self.apply_freqs()
            self.fh_callback()
        else:
            dialog = wx.MessageDialog(self, "Are you sure?", "Stop", style=wx.ICON_WARNING | wx.OK | wx.CANCEL)
            
            if dialog.ShowModal() == wx.ID_OK:
                self.fh_callback()

            

    def set_fh_state(self, state: bool) -> None:
        self.running = state
        if self.running:
            self.run_button.SetLabel("Stop Simulation!")
        else:
            self.run_button.SetLabel("Start Simulation!")




if __name__ == "__main__":
    import json
    app = wx.App()
    frame = wx.Frame(None)
    with open("settings.json") as file:
        settings = json.load(file)
    panel = ConfigPanel(frame, settings)
    sizer = wx.BoxSizer()
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Fit()
    frame.Show()
    app.MainLoop()
    with open("settings.json", 'w') as file:
        json.dump(settings, file)