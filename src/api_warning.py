import wx



def api_warning() -> None:
    app = wx.App.Get()
    created = False
    if not app:
        app = wx.App()
        created = True

    mb = wx.MessageBox(
        message=
"""The KiCad API is busy.
This most likely stems from a tool still being selected.
Ensure the PCB Editor is in an idle state, no pop-ups are still open
and any tool is deselected.""",
        caption="KiCad is busy"
    )
    if created:
        app.Destroy()
    pass





if __name__ == "__main__":
    api_warning()