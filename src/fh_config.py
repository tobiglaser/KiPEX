import wx
import wx.adv
from typing import Dict
from os import path


class FHConfigDialog(wx.Dialog):
    def __init__(self, parent: wx.Window | None, config: Dict = {}) -> None:
        super().__init__(parent)
        self.options = {}
        self.config = config
        bs = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(bs)
        fs = wx.BoxSizer()
        fs.AddStretchSpacer(10)
        fs.Add(wx.StaticText(self, label="Input file name"), 0, wx.BOTTOM | wx.TOP, 10)
        fs.AddStretchSpacer(1)
        self.file_name = wx.TextCtrl(self)
        if config.get("file"):
            self.file_name.SetValue(config["file"])
        fs.Add(self.file_name, 20, wx.BOTTOM | wx.TOP, 10)
        fs.AddStretchSpacer(1)
        browse_button = wx.Button(self, label="Browse")
        browse_button.Bind(wx.EVT_BUTTON, self.on_browse)
        fs.Add(browse_button, 0, wx.BOTTOM | wx.TOP, 10)
        
        fs.AddStretchSpacer(5)

        fs.Add(wx.adv.HyperlinkCtrl(
                self,
                label="FastHenry User Guide",
                url="https://www.fastfieldsolvers.com/Download/FastHenry_User_Guide.pdf"
                ),
            0, wx.BOTTOM | wx.TOP | wx.RIGHT, 10)


        
        bs.Add(fs, 0, wx.EXPAND)
        left_grid = wx.FlexGridSizer(2)
        cs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(cs, 0, 0)
        bs.AddSpacer(20)
        cs.Add(left_grid, 1, wx.EXPAND)

        value_options = [
            ("Order for reduced order model", "-r", 0),
            ("Suffix for filenames", "-S", ""),
            ("Order of multipole expansions", "-o", 2),
            ("Tolerance for iteration error rtol", "-t", 0.001),
            ("Tolerance for iteration error atol", "-b", 0.01),
            ("Maximum number of solve iterations", "-n", 200),
            ("Level for initial refinement", "-i", 0),
            ("Radius of the shells", "-R", 0)
            ]
        for label, flag, default in value_options:
            check = wx.CheckBox(self, label=f"{label} ({flag})")
            check.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
            if config.get("options") and config["options"].get(flag):
                check.SetValue(True)
                value = config["options"][flag]
                field = wx.TextCtrl(self, value=str(value))
            else:
                check.SetValue(False)
                field = wx.TextCtrl(self, value=str(default))
                field.Disable()
            self.options[check.Id] = {"check": check, "field": field, "flag": flag}
            left_grid.Add(check, 0, 0)
            left_grid.Add(field, 0, wx.ALIGN_RIGHT)
        
        check_options_left = [
            ("Allow multipole algorithm to refine structure", "-a", True),
            ("Exit after generating ROM", "-M", False),
            #("Print results on the screen", "-O", True)
        ]
        for label, flag, default in check_options_left:
            check = wx.CheckBox(self, label=f"{label} ({flag})")
            value = default
            if config.get("options") and config["options"].get(flag) != None:
                value = config["options"][flag]
            check.SetValue(value)
            #field = wx.TextCtrl(self, value=str(default))
            #field.Show(False)
            self.options[check.Id] = {"check": check, "field": None, "flag": flag}
            left_grid.Add(check, 0, wx.TOP | wx.BOTTOM, 2)
            left_grid.AddStretchSpacer()

        right_grid = wx.FlexGridSizer(2)
        cs.AddSpacer(20)
        cs.Add(right_grid, 0, 0)
        combo_options = [
            ("Matrix solution method", "-s", "iterative", ["iterative", "ludecomp"]),
            ("Method for matrix-vector product", "-m", "multi", ["multi", "direct"]),
            ("Preconditioning method", "-p", "cube", ["on","off", "loc", "posdef", "cube", "seg", "diag", "shells"]),
            ("Number in partitioning levels", "-l", "auto", ["auto", "1?", "2?", "3?", "4?"]),
            ("Visualization mode", "-f", "off", ["off", "simple", "refined", "both", "hierarchy"]),
            ("Ground plane appearance", "-g", "off", ["on", "off", "thin", "thick"]),
            ("Dump internal matrices to files", "-d", "off", ["on", "off", "mrl", "mzmt", "grids", "meshes", "pre", "a", "m", "rl", "ls"]),
            ("Type of file to dump", "-k", "none", ["matlab", "text", "both"]),
            ("Restrict computation to ports", "-x", "", [""])
        ]
        
        for label, flag, default, choices in combo_options:
            check = wx.CheckBox(self, label=f"{label} ({flag})")
            check.Bind(wx.EVT_CHECKBOX, self.on_checkbox)
            if config.get("options") and config["options"].get(flag):
                check.SetValue(True)
                value = config["options"][flag]
                field = wx.ComboBox(self, value=str(value), choices=choices)
            else:
                check.SetValue(False)
                field = wx.ComboBox(self, value=str(default), choices=choices)
                field.Disable()
            self.options[check.Id] = {"check": check, "field": field, "flag": flag}
            right_grid.Add(check, 0, 0)
            right_grid.Add(field, 0, wx.ALIGN_RIGHT | wx.RIGHT, 5)
            if flag == "-x":
                # this would require analysing the file for ".external" lines
                # which is entanglement I don't want to commit to for now.
                check.Disable()
                field.Disable()

        check_options_right = [
            ("Regurgitate geometry", "-v", False),
            ("Print debugging information", "-D", False)
        ]
        for label, flag, default in check_options_right:
            check = wx.CheckBox(self, label=f"{label} ({flag})")
            value = default
            if config.get("options") and config["options"].get(flag):
                value = config["options"][flag]
            check.SetValue(value)
            self.options[check.Id] = {"check": check, "field": None, "flag": flag}
            right_grid.Add(check, 0, wx.TOP | wx.BOTTOM, 2)
            right_grid.AddStretchSpacer()

        bbs = wx.BoxSizer(wx.HORIZONTAL)
        bbs.AddStretchSpacer(10)
        cancel_button = wx.Button(self, label="Cancel")
        cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)
        bbs.Add(cancel_button, 0, wx.BOTTOM | wx.TOP, 10)
        bbs.AddStretchSpacer(1)
        reset_button = wx.Button(self, label="Reset")
        reset_button.Bind(wx.EVT_BUTTON, self.on_reset)
        bbs.Add(reset_button, 0, wx.BOTTOM | wx.TOP, 10)
        bbs.AddStretchSpacer(1)
        apply_button = wx.Button(self, label="Apply")
        apply_button.Bind(wx.EVT_BUTTON, self.on_apply)
        bbs.Add(apply_button, 0, wx.BOTTOM | wx.TOP, 10)
        bbs.AddStretchSpacer(10)
        bs.Add(bbs, 0, wx.EXPAND)

        self.Fit()

    def on_checkbox(self, event: wx.Event) -> None:
        option = self.options[event.Id]
        state = option["check"].GetValue()
        if state:
            option["field"].Enable()
        else:
            option["field"].Disable()

    def on_browse(self, event) -> None:
        dir = path.dirname(self.file_name.GetValue()) or "~"
        dialog = wx.FileDialog(
            self,
            wildcard="*.inp",
            style=wx.FD_FILE_MUST_EXIST,
            defaultDir=dir)
        dialog.ShowModal()
        self.file_name.SetValue(dialog.GetPath())

    def on_apply(self, event) -> None:
        config = {}
        config["file"] = self.file_name.GetValue()
        config["options"] = {}
        for option in self.options.values():
            if option["check"].GetValue() and option.get("field"):
                config["options"][option["flag"]] = option["field"].GetValue()
            elif not option.get("field"):
                config["options"][option["flag"]] = option["check"].GetValue()
        self.config = config
        self.Close()

    def on_reset(self, event) -> None:
        self.config = {}
        self.Close()
    
    def on_cancel(self, event) -> None:
        self.Close()


if  __name__ == "__main__":
    import json
    with open("settings.json") as file:
        settings = json.load(file)

    app = wx.App()
    dialog = FHConfigDialog(None, settings.get("fh_config", {}))

    frame = wx.Frame(None)

    dialog.ShowModal()

    print(dialog.config)

    with open("settings.json", 'w') as file:
        settings["fh_config"] = dialog.config
        json.dump(settings, file)
