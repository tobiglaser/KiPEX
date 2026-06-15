import wx
from fh_config import FHConfigDialog
from typing import Dict, Callable
from engineering_notation import EngUnit
from os import path

class ConfigPanel(wx.Panel):
    def __init__(self, parent: wx.Window, settings: Dict = {}, project_name: str = "", fh_callback: Callable = print, gen_callback: Callable = print) -> None:
        super().__init__(parent=parent)
        self.settings = settings
        self.fh_callback = fh_callback
        self.gen_callback = gen_callback
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
        inner_freq_sizer.Add(wx.StaticText(self, label="fmin / Hz"), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        inner_freq_sizer.AddStretchSpacer()
        inner_freq_sizer.Add(wx.StaticText(self, label="fmax / Hz"), 1, wx.ALIGN_CENTER | wx.TOP, 5)
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

        spice_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, "SPICE-Model")
        inner_spice_sizer = wx.FlexGridSizer(5)
        inner_spice_sizer.AddGrowableCol(0, 1)
        inner_spice_sizer.AddGrowableCol(2, 1)
        inner_spice_sizer.AddGrowableCol(4, 1)
        sizer.Add(spice_sizer, 0, wx.EXPAND | wx.ALL, 5)
        spice_sizer.Add(inner_spice_sizer, 1, wx.EXPAND, 5)
        inner_spice_sizer.Add(wx.StaticText(self, label=""), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        inner_spice_sizer.AddStretchSpacer()
        inner_spice_sizer.Add(wx.StaticText(self, label="Filename"), 1, wx.ALIGN_CENTER | wx.TOP, 5)
        inner_spice_sizer.AddStretchSpacer()
        inner_spice_sizer.Add(wx.StaticText(self, label="Frequency / Hz"), 1, wx.ALIGN_CENTER | wx.TOP | wx.RIGHT, 5)
        self.spice_box = wx.CheckBox(self,label="Export")
        export = self.settings.get("spice", {}).get("gen_spice", False)
        self.spice_box.SetValue(export)
        inner_spice_sizer.Add(self.spice_box, 1, wx.TOP | wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTER, 5)
        inner_spice_sizer.AddSpacer(5)
        file_name = self.settings.get("spice", {}).get("file_name", "PCB.sub")
        self.spice_filename_box = wx.ComboBox(self, value=file_name, choices=["PCB.sub"])
        inner_spice_sizer.Add(self.spice_filename_box, 1, wx.EXPAND | wx.ALL, 5)
        inner_spice_sizer.AddSpacer(5)
        freq = self.settings.get("spice", {}).get("frequency", "100kHz")
        self.spice_freq_box = wx.TextCtrl(self, value=freq, style=wx.TE_RIGHT)
        inner_spice_sizer.Add(self.spice_freq_box, 1, wx.EXPAND | wx.TOP | wx.BOTTOM | wx.RIGHT, 5)

        inp_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="FastHenry-Model")
        sizer.Add(inp_sizer, 0, wx.EXPAND | wx.ALL, 5)
        fh_file_name = self.settings.get("fh_config", {}).get("file", path.abspath(f"{project_name}.inp"))
        fh_file_choices = self.settings.get("fh_config", {}).get("last_files", [path.abspath(f"{project_name}.inp")])
        self.fh_file_box = wx.ComboBox(self,value=fh_file_name, choices=fh_file_choices)
        inp_sizer.Add(self.fh_file_box, 1, wx.EXPAND | wx.ALL, 5)
        browse_button = wx.Button(self, label="Browse")
        inp_sizer.Add(browse_button, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, 5)
        browse_button.Bind(wx.EVT_BUTTON, self.on_browse)

        quad_sizer = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Zone Rasterization")
        sizer.Add(quad_sizer, 0, wx.EXPAND | wx.ALL, 5)
        upper = self.settings.get("quad_split", {}).get("upper", 1)
        lower = self.settings.get("quad_split", {}).get("lower", 0.1)
        self.upper_limit_box = wx.SpinCtrlDouble(self, min=0.01, max=20, inc=0.05, initial=upper)
        self.lower_limit_box = wx.SpinCtrlDouble(self, min=0.01, max=20, inc=0.05, initial=lower)
        inner_quad_sizer = wx.FlexGridSizer(3)
        quad_sizer.Add(inner_quad_sizer, 1, wx.EXPAND)
        inner_quad_sizer.AddGrowableCol(0, 1)
        inner_quad_sizer.AddGrowableCol(2, 1)
        inner_quad_sizer.Add(wx.StaticText(self, label="Upper Splitting Limit / mm"), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        inner_quad_sizer.AddSpacer(5)
        inner_quad_sizer.Add(wx.StaticText(self, label="Lower Splitting Limit / mm"), 1, wx.ALIGN_CENTER | wx.TOP | wx.LEFT, 5)
        inner_quad_sizer.Add(self.upper_limit_box, 1, wx.TOP | wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTER, 5)
        inner_quad_sizer.AddSpacer(5)
        inner_quad_sizer.Add(self.lower_limit_box, 1, wx.TOP | wx.BOTTOM | wx.LEFT | wx.ALIGN_CENTER, 5)

        self.visualization_box = wx.CheckBox(self, label="Visualize on Generation")
        self.visualization_box.SetValue(self.settings.get("visualize", True))
        sizer.Add(self.visualization_box, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        sizer.AddSpacer(10)

        bottom_sizer = wx.FlexGridSizer(2)
        sizer.Add(bottom_sizer, 1, wx.EXPAND)
        bottom_sizer.AddGrowableCol(0, 1)
        bottom_sizer.AddGrowableCol(1, 1)
        bottom_sizer.AddGrowableRow(0, 1)
        bottom_sizer.AddGrowableRow(1, 2)

        fila_button = wx.Button(self, label="Filamentization")
        config_fh_button = wx.Button(self, label="Configure FastHenry")
        self.gen_button = wx.Button(self, label="Generate Model")
        self.run_button = wx.Button(self, label="Start Simulation!")
        bottom_sizer.Add(fila_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(config_fh_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(self.gen_button, 1, wx.EXPAND | wx.ALL, 5)
        bottom_sizer.Add(self.run_button, 1, wx.EXPAND | wx.ALL, 5)
        fila_button.Bind(wx.EVT_BUTTON, self.on_filament)
        fila_button.Disable()
        config_fh_button.Bind(wx.EVT_BUTTON, self.on_config_fh)
        self.gen_button.Bind(wx.EVT_BUTTON, self.on_generate)
        self.run_button.Bind(wx.EVT_BUTTON, self.on_run_fh)

    def apply_freqs(self) -> None:
        self.settings["freqs"] = {}
        self.settings["freqs"]["str_min"] = self.spin1.GetValue()
        self.settings["freqs"]["min"] = float(EngUnit(self.spin1.GetValue().replace(',', '.'), 3, 0, "Hz"))
        self.settings["freqs"]["str_max"] = self.spin2.GetValue()
        self.settings["freqs"]["max"] = float(EngUnit(self.spin2.GetValue().replace(',', '.'), 3, 0, "Hz"))
        self.settings["freqs"]["ndec"] = self.spin3.GetValue()

    def apply_options(self) -> None:
        self.settings["spice"] = {}
        self.settings["spice"]["gen_spice"] = self.spice_box.GetValue()
        self.settings["spice"]["file_name"] = self.spice_filename_box.GetValue()
        self.settings["spice"]["frequency"] = self.spice_freq_box.GetValue()

        self.settings["quad_split"] = {}
        self.settings["quad_split"]["upper"] = self.upper_limit_box.GetValue()
        self.settings["quad_split"]["lower"] = self.lower_limit_box.GetValue()

        self.settings["visualize"] = self.visualization_box.GetValue()

        if not self.settings.get("fh_config"):
            dialog = FHConfigDialog(self, {})
            dialog.on_apply(None)
            self.settings["fh_config"] = dialog.config
        file_str = self.fh_file_box.GetValue()
        self.settings["fh_config"]["file"] = file_str
        if not file_str in self.fh_file_box.GetStrings():
            self.fh_file_box.Append(file_str)
        if self.settings["fh_config"].get("last_files"):
            if not file_str in self.settings["fh_config"]["last_files"]:
                self.settings["fh_config"]["last_files"].append(file_str)
        else:
            self.settings["fh_config"]["last_files"] = [file_str]

    def on_config_fh(self, event: wx.Event) -> None:
        dialog = FHConfigDialog(self, self.settings.get("fh_config", {}))
        dialog.ShowModal()
        self.settings["fh_config"] = dialog.config

    def on_filament(self, event: wx.Event) -> None:
        print("Placeholder!")

    def on_generate(self, event: wx.Event) -> None:
        self.apply_freqs()
        self.apply_options()
        self.gen_callback()

    def on_run_fh(self, event: wx.Event) -> None:
        if not self.running:
            self.apply_freqs()
            self.apply_options()
            self.fh_callback()
        else:
            dialog = wx.MessageDialog(self, "Are you sure?", "Stop", style=wx.ICON_WARNING | wx.OK | wx.CANCEL)
            
            if dialog.ShowModal() == wx.ID_OK:
                self.fh_callback()

    def on_browse(self, event) -> None:
        dir = path.dirname(self.fh_file_box.GetValue()) or "~"
        dialog = wx.FileDialog(
            self,
            wildcard="*.inp",
            style=wx.FD_SAVE,
            defaultDir=dir)
        dialog.ShowModal()
        if dialog.GetPath():
            self.fh_file_box.SetValue(dialog.GetPath())

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
    try:
        with open("settings.json") as file:
            settings = json.load(file)
    except:
        settings = {}
    panel = ConfigPanel(frame, settings)
    sizer = wx.BoxSizer()
    sizer.Add(panel, 1, wx.EXPAND)
    frame.SetSizer(sizer)
    frame.Fit()
    frame.Show()
    app.MainLoop()
    with open("settings.json", 'w') as file:
        json.dump(settings, file)