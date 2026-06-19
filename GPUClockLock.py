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
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def get_supported_graphics_clock_range(gpu_index):
    try:
        output = run_command([
            "nvidia-smi",
            "-i", str(gpu_index),
            "-q",
            "-d", "SUPPORTED_CLOCKS"
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

        max_clock = int(max_clock)
        min_clock = min_supported if min_supported is not None else 0
        display_max = max_supported if max_supported is not None else max_clock

        gpus.append({
            "index": index,
            "name": name,
            "current": int(current_clock),
            "min": int(min_clock),
            "max": int(max_clock),
            "display_max": int(display_max)
        })

    return gpus


def lock_gpu_clock(gpu_index, target_clock):
    run_command([
        "nvidia-smi",
        "-i", str(gpu_index),
        "-lgc", f"{target_clock},{target_clock}"
    ])


def unlock_gpu_clock(gpu_index):
    run_command([
        "nvidia-smi",
        "-i", str(gpu_index),
        "-rgc"
    ])


class GPUClockLockerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("735x285")
        self.root.resizable(False, False)
        self.root.after(100, self._set_icon)

        self.config = load_config()
        self.gpus = []
        self.locked_gpu_index = None

        self.gpu_var = tk.StringVar()
        self.percent_var = tk.StringVar()

        self.gpu_name_var = tk.StringVar(value="No GPU selected")
        self.status_var = tk.StringVar(value="Unlocked")
        self.current_var = tk.StringVar(value="-- MHz")
        self.target_var = tk.StringVar(value="--")
        self.min_var = tk.StringVar(value="-- MHz")
        self.max_var = tk.StringVar(value="-- MHz")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        outer = ttk.Frame(root, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Select GPU").grid(row=0, column=0, columnspan=2, sticky="w")

        self.gpu_dropdown = ttk.Combobox(
            outer,
            textvariable=self.gpu_var,
            state="readonly",
            width=92
        )
        self.gpu_dropdown.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 16))
        self.gpu_dropdown.bind("<<ComboboxSelected>>", self.on_gpu_selected)

        left = ttk.Frame(outer)
        left.grid(row=2, column=0, sticky="nw", padx=(0, 24))

        right = ttk.LabelFrame(outer, padding=14)
        right.grid(row=2, column=1, sticky="nw")

        ttk.Label(left, text="Target %").grid(row=0, column=0, sticky="w")

        self.percent_dropdown = ttk.Combobox(
            left,
            textvariable=self.percent_var,
            state="readonly",
            width=10,
            values=[f"{p}%" for p in TARGET_PERCENTAGES]
        )
        self.percent_dropdown.grid(row=1, column=0, sticky="w", pady=(4, 18))
        self.percent_dropdown.bind("<<ComboboxSelected>>", self.on_percent_selected)

        ttk.Button(left, text="Lock", width=14, command=self.lock_selected_gpu).grid(
            row=2,
            column=0,
            sticky="w",
            pady=3
        )

        ttk.Button(left, text="Unlock", width=14, command=self.unlock_selected_gpu).grid(
            row=3,
            column=0,
            sticky="w",
            pady=3
        )

        ttk.Button(left, text="Refresh", width=14, command=self.refresh_gpus).grid(
            row=4,
            column=0,
            sticky="w",
            pady=3
        )

        ttk.Label(
            right,
            textvariable=self.gpu_name_var,
            width=44
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.add_info_row(right, 1, "Status", self.status_var)
        self.add_info_row(right, 3, "Current", self.current_var)
        self.add_info_row(right, 4, "Target", self.target_var)
        self.add_info_row(right, 5, "Minimum", self.min_var)
        self.add_info_row(right, 6, "Maximum", self.max_var)

        self.load_saved_percent()
        self.refresh_gpus()

    def add_info_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label, width=10).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Label(parent, textvariable=variable, width=30).grid(row=row, column=1, sticky="w", pady=3)

    def load_saved_percent(self):
        try:
            saved_percent = int(self.config.get("target_percent", 100))
        except Exception:
            saved_percent = 100

        if saved_percent > 100:
            saved_percent = 100

        if saved_percent < 15:
            saved_percent = 15

        if saved_percent % 5 != 0:
            saved_percent = 100

        self.percent_var.set(f"{saved_percent}%")

    def get_target_percent(self):
        try:
            percent = int(self.percent_var.get().replace("%", ""))
        except Exception:
            percent = 100

        if percent > 100:
            percent = 100

        if percent < 15:
            percent = 15

        if percent % 5 != 0:
            percent = 100

        return percent

    def calculate_target_clock(self, max_clock):
        percent = self.get_target_percent()
        return int(max_clock * percent / 100)

    def gpu_dropdown_label(self, gpu):
        return (
            f'{gpu["index"]}: {gpu["name"]} | '
            f'min {gpu["min"]} MHz | max {gpu["display_max"]} MHz'
        )

    def refresh_gpus(self):
        try:
            self.gpus = get_gpus()

            self.gpu_dropdown["values"] = [
                self.gpu_dropdown_label(gpu) for gpu in self.gpus
            ]

            if not self.gpus:
                self.gpu_dropdown.set("")
                self.gpu_name_var.set("No NVIDIA GPU found")
                self.status_var.set("Unlocked")
                self.current_var.set("-- MHz")
                self.target_var.set("--")
                self.min_var.set("-- MHz")
                self.max_var.set("-- MHz")
                return

            saved_gpu_index = str(self.config.get("last_gpu_index", ""))
            selected_dropdown_index = 0

            for i, gpu in enumerate(self.gpus):
                if gpu["index"] == saved_gpu_index:
                    selected_dropdown_index = i
                    break

            self.gpu_dropdown.current(selected_dropdown_index)
            self.update_info_panel(self.gpus[selected_dropdown_index])

        except Exception as error:
            messagebox.showerror("Refresh failed", str(error))


    def schedule_post_change_refreshes(self):
        # NVIDIA may take a moment to report the new current clock after lock/unlock.
        # These are one-shot refreshes, not continuous polling.
        self.root.after(500, self.refresh_gpus)
        self.root.after(1500, self.refresh_gpus)
        self.root.after(3000, self.refresh_gpus)

    def selected_gpu(self):
        selected = self.gpu_dropdown.current()

        if selected < 0 or selected >= len(self.gpus):
            raise RuntimeError("No GPU selected")

        return self.gpus[selected]

    def on_gpu_selected(self, event=None):
        gpu = self.selected_gpu()
        self.config["last_gpu_index"] = gpu["index"]
        save_config(self.config)
        self.update_info_panel(gpu)

    def on_percent_selected(self, event=None):
        percent = self.get_target_percent()
        self.config["target_percent"] = percent
        save_config(self.config)

        try:
            gpu = self.selected_gpu()
            self.update_info_panel(gpu)
        except Exception:
            pass

    def lock_selected_gpu(self):
        try:
            selected_gpu = self.selected_gpu()
            refreshed_gpus = get_gpus()

            gpu = next(
                item for item in refreshed_gpus
                if item["index"] == selected_gpu["index"]
            )

            percent = self.get_target_percent()
            target_clock = self.calculate_target_clock(gpu["max"])

            self.config["last_gpu_index"] = gpu["index"]
            self.config["target_percent"] = percent
            save_config(self.config)

            lock_gpu_clock(gpu["index"], target_clock)

            self.locked_gpu_index = gpu["index"]
            self.status_var.set("Locked")
            self.update_info_panel(gpu)
            self.schedule_post_change_refreshes()

        except Exception as error:
            messagebox.showerror("Lock failed", str(error))

    def unlock_selected_gpu(self):
        try:
            gpu = self.selected_gpu()
            unlock_gpu_clock(gpu["index"])

            if self.locked_gpu_index == gpu["index"]:
                self.locked_gpu_index = None

            self.status_var.set("Unlocked")
            self.schedule_post_change_refreshes()

        except Exception as error:
            messagebox.showerror("Unlock failed", str(error))

    def unlock_on_exit(self):
        if self.locked_gpu_index is None:
            return

        try:
            unlock_gpu_clock(self.locked_gpu_index)
        except Exception:
            pass

    def _set_icon(self):
        try:
            base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            self.root.wm_iconbitmap(os.path.join(base, "GPUClockLockIcon.ico"))
        except Exception:
            pass

    def on_close(self):
        self.unlock_on_exit()
        self.root.destroy()

    def update_info_panel(self, gpu):
        percent = self.get_target_percent()
        target_clock = self.calculate_target_clock(gpu["max"])

        self.gpu_name_var.set(gpu["name"])
        self.current_var.set(f'{gpu["current"]} MHz')
        self.target_var.set(f'{percent}% ({target_clock} MHz)')
        self.min_var.set(f'{gpu["min"]} MHz')
        self.max_var.set(f'{gpu["display_max"]} MHz')


if __name__ == "__main__":
    root = tk.Tk()
    app = GPUClockLockerApp(root)
    root.mainloop()