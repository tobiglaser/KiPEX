from os import path, mkdir
from platform import system
import json
from wx import App, FileDialog, MessageDialog, OK, FD_FILE_MUST_EXIST
import wx
from wx.adv import HyperlinkCtrl

def ensure_settings_exist(settings_dir: str, settings_file: str) -> None:
    """Creates an empty settings.json if none exists."""
    if not path.exists(settings_dir):
        mkdir(settings_dir)
    settings_path = path.join(settings_dir, settings_file)
    if not path.exists(settings_path):
        with open(settings_path, 'w') as file:
            file.write('{"version": 0}')


class FHDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(panel, label="FastHenry was not found."), 0, wx.ALL | wx.CENTER | wx.ALIGN_CENTER, 10)
        hyperlink = HyperlinkCtrl(panel, wx.ID_ANY, "Download FastHenry here", "https://github.com/tobiglaser/FastHenry2-sam/releases/latest")
        sizer.Add(hyperlink, 0, wx.ALL | wx.CENTER, 10)
        ok = wx.Button(panel, wx.ID_OK, "OK")
        ok.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_OK))
        sizer.Add(ok, 0, wx.ALL | wx.CENTER, 10)
        panel.SetSizer(sizer)





def ensure_fasthenry_path(settings: dict) -> None:
    """Prompts user for FH location, exits if not valid."""

    if not settings.get("fasthenry_path") or not path.exists(settings.get("fasthenry_path", "")):
        suffix = ".exe" if system() == "Windows" else ""
        md = FHDialog(None, "FastHenry not found")
        md.ShowModal()
        md.Destroy()
        fd = FileDialog(None,
                        message=f"Specify fasthenry{suffix} location. See GitHub README.md for installation instructions.",
                        defaultDir='~',
                        wildcard=f"fasthenry{suffix}",
                        style=FD_FILE_MUST_EXIST,
                        )
        fd.ShowModal()
        fh_path = fd.GetPath()
        if not fh_path.endswith(f"fasthenry{suffix}"):
            exit()
        settings["fasthenry_path"] = fh_path
        

if __name__ == "__main__":
    app = wx.App()
    ensure_fasthenry_path({})