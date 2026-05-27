import wx
from typing import Callable
from platform import system
from time import perf_counter

class Executer:
    class Process(wx.Process):
        def __init__(self, parent: wx.Window | None, timer: wx.Timer, timer_callback):
            super().__init__(parent)
            self.Redirect()
            self.timer = timer
            self.callback = timer_callback
            self.exit_code = None
        def OnTerminate(self, pid: int, status: int) -> None:
            self.exit_code = status
            self.callback(None)
            self.timer.Stop()
            return super().OnTerminate(pid, status)

    def __init__(self, parent: wx.Window, log_area: wx.TextCtrl, log_file_path: str | None = None, state_callback: Callable = print) -> None:
        self.parent = parent
        self.log_area = log_area
        self.timer = wx.Timer(parent)
        self.state_callback = state_callback
        parent.Bind(wx.EVT_TIMER, self.on_timer, self.timer)

    def on_timer(self, event):
        #print("TimeOrTerm:")
        out = self.process.GetInputStream()
        err = self.process.GetErrorStream()
        if out.CanRead():
            str = out.read().decode()
            #print("out: ", str)
            self.log_area.AppendText(str)
            if "Frequency" in str:
                self.freq_counter += 1
                if self.freq_counter > 1:
                    self.state_callback(True, "partial")
        if err.CanRead():
            str = err.read().decode()
            #print("err: ", str)
            color = self.log_area.GetDefaultAttributes().colFg
            if str:
                self.log_area.SetDefaultStyle(wx.TextAttr(wx.RED))
                self.log_area.AppendText(f"\nError: {str}")
                self.log_area.SetDefaultStyle(wx.TextAttr(color))

    def run_FH(self, command: str) -> None:
        self.timer.Start(100)
        self.start_time = perf_counter()
        self.state_callback(True, "started")
        self.process = self.Process(self.parent, self.timer, self.on_timer)
        self.pid = wx.Execute(command, callback=self.process)
        self.process.Bind(wx.EVT_END_PROCESS, handler=self.on_ended)
        self.log_area.AppendText("Started FastHenry " + str(self.pid) + "\n")
        self.freq_counter = 0

    def kill_FH(self):
        signal = wx.SIGTERM
        if system() == "Windows":
            signal = wx.SIGKILL
        self.process.Kill(self.pid, signal)

    def on_ended(self, event: wx.Event) -> None:
        self.stop_time = perf_counter()
        self.log_area.AppendText("FastHenry stopped ")
        self.log_area.AppendText(f"after {self.stop_time - self.start_time:.1f}s\n")
        self.log_area.AppendText("Exit code: " + str(self.process.exit_code) + "\n")
        state = "messy"
        if self.process.exit_code == 0:
            state = "clean"
        self.state_callback(False, state)


if __name__ == "__main__":
    app = wx.App()
    frame = wx.Frame(None)
    bs = wx.BoxSizer(wx.VERTICAL)
    tc = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.HSCROLL | wx.TE_READONLY)
    bs.Add(tc, 1, wx.EXPAND)
    executer = Executer(frame, tc, "log.txt")

    def on_run(event):
        executer.run_FH("/home/tobi/Schreibtisch/FastHenry2-Sam/bin/fasthenry -Somimo pin-con7.inp")
    def on_kill(event):
        executer.kill_FH()

    btn = wx.Button(frame, label="Start")
    btn.Bind(wx.EVT_BUTTON, on_run)
    bs.Add(btn, 0, wx.CENTER)
    btn = wx.Button(frame, label="Kill")
    btn.Bind(wx.EVT_BUTTON, on_kill)
    bs.Add(btn, 0, wx.CENTER)

    frame.SetSizer(bs)
    frame.Show()
    app.MainLoop()
