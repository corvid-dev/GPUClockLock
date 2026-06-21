import json
import os
import re
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox


APP_TITLE = "GPUClockLock"
TARGET_PERCENTAGES = list(range(100, 14, -5))

CONFIG_DIR = os.path.join(os.getenv("APPDATA"), APP_TITLE)
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ── theme ─────────────────────────────────────────────────────────────────────
APP_BG     = "#1e1e1e"
PANEL_BG   = "#2a2a2a"
ACCENT     = "#00b894"
ACCENT_OFF = "#e17055"
TEXT       = "#ececec"
MUTED      = "#888888"
FONT       = ("Segoe UI", 9)
FONT_SM    = ("Segoe UI", 8)
FONT_BOLD  = ("Segoe UI", 10, "bold")


# ── backend ───────────────────────────────────────────────────────────────────

def run_command(command):
    try:
        startupinfo = None
        creationflags = 0
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW
        return subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
            startupinfo=startupinfo,
            creationflags=creationflags
        ).strip()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.output.strip() if error.output else str(error))


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_supported_graphics_clock_range(gpu_index):
    try:
        output = run_command([
            "nvidia-smi", "-i", str(gpu_index), "-q", "-d", "SUPPORTED_CLOCKS"
        ])
        clocks = []
        for line in output.splitlines():
            match = re.search(r"Graphics\s*:\s*(\d+)\s*MHz", line)
            if match:
                clocks.append(int(match.group(1)))
        if clocks:
            return min(clocks), max(clocks)
    except Exception:
        pass
    return None, None


def get_gpus():
    output = run_command([
        "nvidia-smi",
        "--query-gpu=index,name,clocks.current.graphics,clocks.max.graphics",
        "--format=csv,noheader,nounits"
    ])
    gpus = []
    for line in output.splitlines():
        index, name, current_clock, max_clock = [x.strip() for x in line.split(",")]
        min_supported, max_supported = get_supported_graphics_clock_range(index)
        max_clock   = int(max_clock)
        min_clock   = min_supported if min_supported is not None else 0
        display_max = max_supported if max_supported is not None else max_clock
        gpus.append({
            "index": index, "name": name,
            "current": int(current_clock),
            "min": int(min_clock), "max": int(max_clock),
            "display_max": int(display_max)
        })
    return gpus


def lock_gpu_clock(gpu_index, target_clock):
    run_command(["nvidia-smi", "-i", str(gpu_index), "-lgc",
                 f"{target_clock},{target_clock}"])


def unlock_gpu_clock(gpu_index):
    run_command(["nvidia-smi", "-i", str(gpu_index), "-rgc"])


# ── app ───────────────────────────────────────────────────────────────────────

class GPUClockLockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.configure(bg=APP_BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._set_icon)

        self.config          = load_config()
        self.gpus            = []
        self.locked_gpu_index = None

        self.gpu_var      = tk.StringVar()
        self.percent_var  = tk.StringVar()
        self.gpu_name_var = tk.StringVar(value="No GPU selected")
        self.status_var   = tk.StringVar(value="● UNLOCKED")
        self.current_var  = tk.StringVar(value="-- MHz")
        self.target_var   = tk.StringVar(value="--")
        self.min_var      = tk.StringVar(value="-- MHz")
        self.max_var      = tk.StringVar(value="-- MHz")

        self._build_ui()
        self._style_combobox()
        self.load_saved_percent()
        self.refresh_gpus()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # status bar
        self._status_lbl = tk.Label(root, textvariable=self.status_var,
                                     bg=APP_BG, fg=ACCENT,
                                     font=FONT_BOLD, anchor="w")
        self._status_lbl.grid(row=0, column=0, columnspan=2,
                               sticky="ew", padx=10, pady=6)

        tk.Frame(root, bg="#333", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10)

        # GPU dropdown
        tk.Label(root, text="GPU", bg=APP_BG, fg=MUTED,
                 font=FONT_SM, anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 0))

        self.gpu_dropdown = ttk.Combobox(root, textvariable=self.gpu_var,
                                          state="readonly", font=FONT)
        self.gpu_dropdown.grid(row=3, column=0, columnspan=2,
                                sticky="ew", padx=10, pady=(2, 6))
        self.gpu_dropdown.bind("<<ComboboxSelected>>", self.on_gpu_selected)

        tk.Frame(root, bg="#333", height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=10)

        # left column — target % + buttons
        left = tk.Frame(root, bg=APP_BG)
        left.grid(row=5, column=0, sticky="nw", padx=10, pady=10)

        tk.Label(left, text="Target %", bg=APP_BG, fg=MUTED,
                 font=FONT_SM, anchor="w").grid(row=0, column=0, sticky="w")

        self.percent_dropdown = ttk.Combobox(
            left, textvariable=self.percent_var,
            state="readonly", width=10, font=FONT,
            values=[f"{p}%" for p in TARGET_PERCENTAGES])
        self.percent_dropdown.grid(row=1, column=0, sticky="w", pady=(4, 12))
        self.percent_dropdown.bind("<<ComboboxSelected>>", self.on_percent_selected)

        for i, (label, cmd) in enumerate([
            ("Lock",    self.lock_selected_gpu),
            ("Unlock",  self.unlock_selected_gpu),
            ("Refresh", self.refresh_gpus),
        ]):
            tk.Button(left, text=label, width=12,
                      bg=PANEL_BG, fg=TEXT, font=FONT,
                      relief="flat", cursor="hand2",
                      activebackground="#444", activeforeground=TEXT,
                      command=cmd).grid(row=2 + i, column=0,
                                        sticky="w", pady=3)

        # right column — info panel
        right = tk.Frame(root, bg=PANEL_BG)
        right.grid(row=5, column=1, sticky="nw", padx=(0, 10), pady=10)

        tk.Label(right, textvariable=self.gpu_name_var,
                 bg=PANEL_BG, fg=TEXT, font=FONT,
                 anchor="w", width=46).grid(
            row=0, column=0, columnspan=2,
            sticky="w", padx=10, pady=(10, 8))

        tk.Frame(right, bg="#333", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10)

        for i, (label, var) in enumerate([
            ("Current", self.current_var),
            ("Target",  self.target_var),
            ("Minimum", self.min_var),
            ("Maximum", self.max_var),
        ]):
            self._info_row(right, i + 2, label, var)

        tk.Frame(right, bg=PANEL_BG, height=8).grid(
            row=99, column=0, columnspan=2)

        root.columnconfigure(1, weight=1)

    def _info_row(self, parent, row, label, variable):
        tk.Label(parent, text=label, bg=PANEL_BG, fg=MUTED,
                 font=FONT_SM, width=10, anchor="w").grid(
            row=row, column=0, sticky="w", padx=(10, 4), pady=3)
        tk.Label(parent, textvariable=variable, bg=PANEL_BG, fg=TEXT,
                 font=FONT, width=28, anchor="w").grid(
            row=row, column=1, sticky="w", padx=(0, 10), pady=3)

    def _style_combobox(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox",
                    fieldbackground=PANEL_BG, background=PANEL_BG,
                    foreground=TEXT, selectbackground=PANEL_BG,
                    selectforeground=TEXT, bordercolor="#444", arrowcolor=TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", PANEL_BG)],
              foreground=[("readonly", TEXT)])

    def _set_icon(self):
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            self.root.wm_iconbitmap(os.path.join(base, "GPUClockLockIcon.ico"))
        except Exception:
            pass

    # ── logic ─────────────────────────────────────────────────────────────────

    def load_saved_percent(self):
        try:
            saved = int(self.config.get("target_percent", 100))
        except Exception:
            saved = 100
        saved = max(15, min(100, saved))
        if saved % 5 != 0:
            saved = 100
        self.percent_var.set(f"{saved}%")

    def get_target_percent(self):
        try:
            percent = int(self.percent_var.get().replace("%", ""))
        except Exception:
            percent = 100
        percent = max(15, min(100, percent))
        if percent % 5 != 0:
            percent = 100
        return percent

    def calculate_target_clock(self, max_clock):
        return int(max_clock * self.get_target_percent() / 100)

    def gpu_dropdown_label(self, gpu):
        return (f'{gpu["index"]}: {gpu["name"]} | '
                f'min {gpu["min"]} MHz | max {gpu["display_max"]} MHz')

    def refresh_gpus(self):
        try:
            self.gpus = get_gpus()
            self.gpu_dropdown["values"] = [self.gpu_dropdown_label(g) for g in self.gpus]
            if not self.gpus:
                self.gpu_dropdown.set("")
                self.gpu_name_var.set("No NVIDIA GPU found")
                self.current_var.set("-- MHz")
                self.target_var.set("--")
                self.min_var.set("-- MHz")
                self.max_var.set("-- MHz")
                return
            saved = str(self.config.get("last_gpu_index", ""))
            sel   = next((i for i, g in enumerate(self.gpus)
                          if g["index"] == saved), 0)
            self.gpu_dropdown.current(sel)
            self.update_info_panel(self.gpus[sel])
        except Exception as e:
            messagebox.showerror("Refresh failed", str(e))

    def schedule_post_change_refreshes(self):
        for delay in (500, 1500, 3000):
            self.root.after(delay, self.refresh_gpus)

    def selected_gpu(self):
        sel = self.gpu_dropdown.current()
        if sel < 0 or sel >= len(self.gpus):
            raise RuntimeError("No GPU selected")
        return self.gpus[sel]

    def on_gpu_selected(self, event=None):
        gpu = self.selected_gpu()
        self.config["last_gpu_index"] = gpu["index"]
        save_config(self.config)
        self.update_info_panel(gpu)

    def on_percent_selected(self, event=None):
        self.config["target_percent"] = self.get_target_percent()
        save_config(self.config)
        try:
            self.update_info_panel(self.selected_gpu())
        except Exception:
            pass

    def lock_selected_gpu(self):
        try:
            selected  = self.selected_gpu()
            refreshed = get_gpus()
            gpu = next(g for g in refreshed if g["index"] == selected["index"])
            target_clock = self.calculate_target_clock(gpu["max"])
            self.config["last_gpu_index"] = gpu["index"]
            self.config["target_percent"]  = self.get_target_percent()
            save_config(self.config)
            lock_gpu_clock(gpu["index"], target_clock)
            self.locked_gpu_index = gpu["index"]
            self._set_status_locked()
            self.update_info_panel(gpu)
            self.schedule_post_change_refreshes()
        except Exception as e:
            messagebox.showerror("Lock failed", str(e))

    def unlock_selected_gpu(self):
        try:
            gpu = self.selected_gpu()
            unlock_gpu_clock(gpu["index"])
            if self.locked_gpu_index == gpu["index"]:
                self.locked_gpu_index = None
            self._set_status_unlocked()
            self.schedule_post_change_refreshes()
        except Exception as e:
            messagebox.showerror("Unlock failed", str(e))

    def unlock_on_exit(self):
        if self.locked_gpu_index is None:
            return
        try:
            unlock_gpu_clock(self.locked_gpu_index)
        except Exception:
            pass

    def on_close(self):
        self.unlock_on_exit()
        self.root.destroy()

    def update_info_panel(self, gpu):
        percent      = self.get_target_percent()
        target_clock = self.calculate_target_clock(gpu["max"])
        self.gpu_name_var.set(gpu["name"])
        self.current_var.set(f'{gpu["current"]} MHz')
        self.target_var.set(f'{percent}% ({target_clock} MHz)')
        self.min_var.set(f'{gpu["min"]} MHz')
        self.max_var.set(f'{gpu["display_max"]} MHz')

    def _set_status_locked(self):
        self.status_var.set("● LOCKED")
        self._status_lbl.config(fg=ACCENT_OFF)

    def _set_status_unlocked(self):
        self.status_var.set("● UNLOCKED")
        self._status_lbl.config(fg=ACCENT)


if __name__ == "__main__":
    root = tk.Tk()
    GPUClockLockerApp(root)
    root.mainloop()