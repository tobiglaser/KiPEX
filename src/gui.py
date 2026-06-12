import wx
from math import ceil
from os import path
import traceback
from typing import Callable
from net_panel import NetPanel
from config_panel import ConfigPanel
from results_panel import ResultsPanel
from fh_runner import Executer
from fh_config import FHConfigDialog
from translator import Translator
from z_mat import Z_mat
from engineering_notation import EngUnit
from version import build_version


#def Error(message: str):
#    app = wx.App()
#    dialog = wx.MessageDialog(None, message, caption="Error")
#    dialog.ShowModal()
#    app.MainLoop()


class App(wx.App):
    def __init__(self, redirect=False, filename=None, useBestVisual=False, clearSigInt=True, project_name: str = "", settings: dict = {}):
        self.settings = settings
        self.project_name = project_name
        super().__init__(redirect, filename, useBestVisual, clearSigInt)
    def OnInit(self):
        if self.project_name:
            title = f"KiPEX{' ' if build_version else ''}{build_version} – {self.project_name}"
        else:
            title = f"KiPEX{' ' if build_version else ''}{build_version}"
        self.frame = wx.Frame(parent=None, title=title or 'KiPEX')
        script_dir = path.dirname(path.abspath(__file__))
        png_path = path.join(script_dir, 'icons', 'icon.png')
        if not path.exists(png_path):
            png_path = path.join(script_dir, '..', 'resources', 'icon.png')
        bmp = wx.Bitmap(png_path, wx.BITMAP_TYPE_PNG)
        icon = wx.Icon(bmp)
        self.frame.SetIcon(icon)
        
        self.splitter = wx.SplitterWindow(self.frame, style=wx.SP_3D|wx.SP_THIN_SASH|wx.SP_NO_XP_THEME|wx.SP_LIVE_UPDATE)
        self.splitter.SetSashGravity(0.35)
        self.splitter.SetMinimumPaneSize(100)

        self.frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.notebook = wx.Notebook(self.splitter)
        #self.frame.GetSizer().Add(self.notebook, 10, wx.EXPAND)
        
        self.log_area = wx.TextCtrl(self.splitter, style=wx.TE_MULTILINE | wx.TE_READONLY)
        #self.frame.GetSizer().Add(self.log_area, 2, wx.EXPAND)
        self.splitter.Initialize(self.notebook)
        #self.splitter.SplitHorizontally(self.notebook, self.log_area)
        self.frame.GetSizer().Add(self.splitter, 1, wx.EXPAND)
        
        #self.panel = wx.Panel(self.frame)
        net_sizer = wx.BoxSizer()
        net_page =wx.Panel(self.notebook)
        net_page.SetSizer(net_sizer)
        self.net_panel = NetPanel(net_page)
        net_sizer.Add(self.net_panel, 10, wx.EXPAND | wx.ALL, 10)
        self.config_panel = ConfigPanel(net_page, self.settings, self.project_name, self.on_run_fh, self.on_generate)
        net_sizer.Add(self.config_panel, 5, wx.EXPAND | wx.ALL, 10)
        self.notebook.AddPage(net_page, "From Nets", True)


        self.results_page = ResultsPanel(self.notebook)
        self.notebook.AddPage(self.results_page, "Results", False)

        self.fh_runner = Executer(self.frame, self.log_area, None, self.on_fh_state)
        self.fh_running = False

#        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page_change)

        return True

#    def on_page_change(self, event: wx.BookCtrlEvent) -> None:
#        self.notebook.GetPage(event.GetSelection()).Fit()
#        print("Hello")

    def run(self):
        #self.on_dpi_change(None)
        #self.on_order_flag(None)
        self.frame.Fit()
        self.notebook.SetMinSize(self.notebook.GetSize())
        nb_height = self.notebook.GetSize().GetHeight()
        frame_size = self.frame.GetSize()
        self.frame.SetSize(wx.Size(frame_size.GetWidth(), frame_size.GetHeight() + 100))
        self.splitter.SplitHorizontally(self.notebook, self.log_area, nb_height)
        self.frame.Show()
        self.MainLoop()
        pass

    def set_net_pads(self, net_pad_dict: dict[str, list[str]]) -> None:
        self.net_panel.set_net_pads(net_pad_dict)


    def set_translator(self, translator: Translator):
        self.translator = translator

    def on_run_fh(self) -> None:
        if not self.fh_running:
            if not self.settings.get("fh_config"):
                dialog = FHConfigDialog(self.frame, {})
                dialog.on_apply(None)
                self.settings["fh_config"] = dialog.config
            fh_path = self.settings["fasthenry_path"]
            file = self.settings["fh_config"].get("file", "")
            if not file: file = "-h"
            suffix = self.settings["fh_config"]["options"].get("-S", "")
            command = fh_path + " " + (f"-S{suffix}" if suffix else "") + " " + file
            self.log_area.AppendText(command + "\n")
            self.fh_runner.run_FH(command)
        else:
            self.fh_runner.kill_FH()

    def on_generate(self) -> None:
        self.translator.reset()
        nets = self.net_panel.plot_list.GetStrings()
        for net in nets:
            if "⚠️" in net:
                mb = wx.MessageBox(f'Ensure distinct Ports in net "{net.removesuffix(" ⚠️")}".', "⚠️", wx.OK | wx.CENTER, self.frame)
                return
            source = self.net_panel.portdict[net]["source"]
            sink   = self.net_panel.portdict[net]["sink"]
            self.translator.add_port_from_netpanel(source, sink, net)
        
        self.translator.set_frequency_range(self.settings["freqs"]["min"], self.settings["freqs"]["max"], self.settings["freqs"]["ndec"])
        self.translator.set_quad_limits(self.settings["quad_split"]["upper"], self.settings["quad_split"]["lower"])
        try:
            error_str = self.translator.translate()
        except:
            error_str = ""
            tb = traceback.format_exc()
            self.log_area.AppendText(f"Exception during Generation:\n {tb}\n")
        if error_str:
            self.log_area.AppendText("Generation Error:\n" + error_str + "\n")
            return
        file_name = self.settings["fh_config"]["file"]
        if path.exists(file_name):
            mb = wx.MessageDialog(
                self.frame,
                f'File already exists:\n"{path.abspath(file_name)}"\nOverwrite?',
                "Overwrite existing File?",
                style=wx.YES_NO | wx.NO_DEFAULT)
            result = mb.ShowModal()
            if result != wx.ID_YES:
                return
        with open(file_name, 'w') as file:
            self.translator.export(file)


    def on_fh_state(self, running: bool, state: str = "messy") -> None:
        self.fh_running = running
        self.config_panel.set_fh_state(running)
        if (running and state == "partial") or (not running and state == "clean"):
            file = "Zc" + self.settings["fh_config"]["options"].get("-S", "")
            self.results_page.read(file + ".csv", file + ".mat")
            self.results_page.lb.SetSelection(self.results_page.lb.GetPageCount() - 1)
            for page in range(self.notebook.GetPageCount()):
                if self.notebook.GetPage(page) == self.results_page:
                    self.notebook.SetSelection(page)
                    break
            if state=="clean" and self.config_panel.spice_box.GetValue():
                z = Z_mat(file + ".csv", file + ".mat")
                filename = self.config_panel.spice_filename_box.GetValue()
                frequency = float(EngUnit(self.config_panel.spice_freq_box.GetValue()))
                if path.exists(filename):
                    mb = wx.MessageDialog(
                        self.frame,
                        f'File already exists:\n"{path.abspath(filename)}"\nOverwrite?',
                        "Overwrite existing File?",
                        style=wx.YES_NO | wx.NO_DEFAULT)
                    result = mb.ShowModal()
                    if result != wx.ID_YES:
                        return
                z.export_spice(filename, frequency)

    # def set_layers(self, layers: list) -> None:
    #     self.layer_list.Set(layers)
    #     self.original_list = layers

    # def set_copper_count(self, n_layers: int = 2) -> None:
    #     self.n_copper_layers = n_layers

    # def set_viewport(self, xmax, xmin, ymax, ymin) -> None:
    #     self.x_min = xmin
    #     self.x_max = xmax
    #     self.y_min = ymin
    #     self.y_max = ymax
    #     self.x = xmax - xmin
    #     self.y = ymax - ymin

    # def reset_plot_list(self):
    #     while self.plot_list.GetCount():
    #         self.plot_list.SetSelection(0)
    #         self.on_left(None)

    # def set_plot_list(self, layers: list):
    #     for layer in layers:
    #         for i, name in enumerate(self.layer_list.GetStrings()):
    #             if name == layer:
    #                 self.layer_list.SetSelection(i)
    #                 self.on_right(None)

    # def preset_all(self, event) -> None:
    #     self.reset_plot_list()
    #     self.flip_flag.Value = False
    #     self.on_flip_flag(None)
    #     new_layers = [
    #         "Edge.Cuts",
    #         "F.Paste",
    #         "F.Mask",
    #         "F.Silkscreen",
    #         "F.Cu",
    #     ]
    #     copper = self.n_copper_layers
    #     for i in range (1, copper // 2):
    #         new_layers.append(f"In{i}.Cu")
    #     print(new_layers)
    #     self.set_plot_list(new_layers)

    # def preset_none(self, event) -> None:
    #     self.reset_plot_list()
    #     self.flip_flag.Value = True
    #     self.on_flip_flag(None)
    #     new_layers = [
    #         "Edge.Cuts",
    #         "B.Paste",
    #         "B.Mask",
    #         "B.Silkscreen",
    #         "B.Cu",
    #     ]
    #     copper = self.n_copper_layers
    #     for i in range(copper // 2, copper - 1):
    #         new_layers.append(f"In{i}.Cu")
    #     print(new_layers)
    #     self.set_plot_list(new_layers)

    # def preset_named(self, event) -> None:
    #     self.reset_plot_list()
    #     self.flip_flag.Value = False
    #     self.on_flip_flag(None)
    #     new_layers = ["F.Cu"]
    #     copper = self.n_copper_layers
    #     for i in range (1, copper - 1):
    #         new_layers.append(f"In{i}.Cu")
    #     new_layers.append("B.Cu")
    #     print(new_layers)
    #     self.set_plot_list(new_layers)
        

    # def on_right(self, event) -> None:
    #     all = self.layer_list.GetStrings()
    #     selections = self.layer_list.GetSelections()
        
    #     new = self.plot_list.GetStrings()
    #     for item in selections:
    #         new.append(all[item])
    #     self.plot_list.Set(new)
        
    #     for item in reversed(selections):
    #         all.remove(all[item])
    #     self.layer_list.Set(all)

    # def on_left(self, event) -> None:
    #     all = self.plot_list.GetStrings()
    #     selections = self.plot_list.GetSelections()

    #     new = self.layer_list.GetStrings()
    #     for item in selections:
    #         new.append(all[item])
        
    #     def find_index(layer: str) -> int:
    #         for i, entry in enumerate(self.original_list):
    #             if entry == layer:
    #                 return i
    #         return -1
    #     new.sort(key=find_index)
    #     self.layer_list.Set(new)
        
    #     for item in reversed(selections):
    #         all.remove(all[item])
    #     self.plot_list.Set(all)

    # def on_up(self, event) -> None:
    #     index = self.plot_list.GetSelection()
    #     if index == 0:
    #         return
        
    #     strings = self.plot_list.GetStrings()
    #     entry = strings[index]
    #     above_entry = strings[index - 1]

    #     strings[index] = above_entry
    #     strings[index - 1] = entry

    #     self.plot_list.Set(strings)
    #     self.plot_list.SetSelection(index - 1)


    # def on_down(self, event):
    #     index = self.plot_list.GetSelection()
    #     strings = self.plot_list.GetStrings()
    #     if index == len(strings) - 1:
    #         return
        
    #     entry = strings[index]
    #     below_entry = strings[index + 1]

    #     strings[index] = below_entry
    #     strings[index + 1] = entry

    #     self.plot_list.Set(strings)
    #     self.plot_list.SetSelection(index + 1)

    # def on_flip_flag(self, event) -> None:
    #     list = self.plot_list.GetStrings()
    #     list.reverse()
    #     self.plot_list.Set(list)

    # def on_order_flag(self, event) -> None:
    #     if self.order_flag.Value:
    #         self.up_button.Disable()
    #         self.down_button.Disable()
    #     else:
    #         self.up_button.Enable()
    #         self.down_button.Enable()


    # def on_dpi_change(self, event) -> None:
    #     INCH = 25.4#mm
    #     self.res_x = ceil(self.dpi_box.Value * self.x / INCH)
    #     self.res_y = ceil(self.dpi_box.Value * self.y / INCH)
    #     self.resolution_label_xy.LabelText = f"\t{self.res_x}x{self.res_y}"
    #     pixels = self.res_x * self.res_y / 1e6
    #     self.resolution_label_mp.LabelText = f"\t {pixels:.2f} MP"

    # def on_shoot(self, event) -> None:
    #     settings = {}
    #     settings["layers"] = self.plot_list.GetStrings()
    #     settings["dpi"] = self.dpi_box.Value
    #     settings["x_res"] = self.res_x
    #     settings["y_res"] = self.res_y
    #     settings["xmin"] = self.x_min
    #     settings["xmax"] = self.x_max
    #     settings["ymin"] = self.y_min
    #     settings["ymax"] = self.y_max
    #     settings["flip"] = self.flip_flag.Value
    #     settings["keep_order"] = self.order_flag.Value
    #     settings["antialiasing"] = self.aa_flag.Value
    #     if self.shoot_callback:
    #         self.shoot_callback(settings)
    
    # def set_callback(self, func: Callable) -> None:
    #     self.shoot_callback = func




if __name__ == "__main__":
    app = App()
    #app.set_viewport(25.4, 0, 50.8, 0)
    #app.set_layers(["a","b","c","d","e", "f", "g", "h", "i", "j", "k", "l"])
    #def print_dict(dict: Dict) -> None:
    #    print(dict)
    #app.set_callback(print_dict)
    app.run()
