import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import os
import json
import threading
import time
import shutil
import re

# ==========================================
# USER TUNING: ALIGNMENT & NUDGING
# ==========================================
HEADER_NUDGE = {
    "Launch": 0, "Device Name": 30, "Main IP": 30, "Main Port": 20,
    "Action": 10, "Pairing Address": 30, "6-Digit Code": 30
}

COL_WIDTHS = [10, 20, 16, 8, 8, 22, 10]

# ==========================================
# PATH CONFIGURATION
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LOCAL_ADB = os.path.join(SCRIPT_DIR, "adb.exe")
WINGET_ADB_DIR = os.path.expandvars(
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools"
)
WINGET_ADB_EXE = os.path.join(WINGET_ADB_DIR, "adb.exe")
CONFIG_FILE = "devices_config.json"

CREATE_NO_WINDOW = 0x08000000

class AndroidManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Win2Phone - ADB Master v4.1")
        self.root.geometry("1100x900") 
        self.root.configure(bg="#f5f5f5")
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)

        self.devices = self.load_config()
        self.entry_map = {} 
        self.connected_ips = set() 
        self.adb_status_text = tk.StringVar(value="ADB: Initializing...")
        self.monitor_active = True
        
        self.create_widgets()
        self.check_adb_integrity()
        
        self.monitor_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self.monitor_thread.start()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_all_changes(self):
        for name, widgets in self.entry_map.items():
            if name in self.devices:
                self.devices[name]['ip'] = widgets['ip'].get().strip()
                self.devices[name]['last_port'] = widgets['port'].get().strip()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.devices, f, indent=4)
            messagebox.showinfo("Saved", "Changes saved to devices_config.json")
        except: pass

    def get_adb_version(self, path):
        if not os.path.exists(path): return None
        try:
            res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=2, creationflags=CREATE_NO_WINDOW)
            match = re.search(r'(\d+\.\d+\.\d+)', res.stdout)
            return match.group(1) if match else "Unknown"
        except: return "Error"

    def check_adb_integrity(self):
        local_ver = self.get_adb_version(LOCAL_ADB)
        winget_ver = self.get_adb_version(WINGET_ADB_EXE)
        if not local_ver or (winget_ver and local_ver != winget_ver):
            self.pull_latest_adb()
            local_ver = self.get_adb_version(LOCAL_ADB)
        self.adb_status_text.set(f"ADB Status: v{local_ver}" if local_ver else "ADB Status: MISSING")

    def pull_latest_adb(self):
        try:
            subprocess.run("taskkill /f /im adb.exe", shell=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
            time.sleep(0.5)
            for f in ["adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll"]:
                src = os.path.join(WINGET_ADB_DIR, f)
                if os.path.exists(src): shutil.copy2(src, SCRIPT_DIR)
            self.check_adb_integrity()
        except: pass

    def create_widgets(self):
        header_bg = tk.Frame(self.root, bg="#263238", height=60)
        header_bg.pack(fill=tk.X)
        tk.Label(header_bg, text="ANDROID MANAGER", font=("Segoe UI", 14, "bold"), bg="#263238", fg="#ffffff").pack(side=tk.LEFT, padx=20, pady=15)
        
        adb_box = tk.Frame(header_bg, bg="#37474f", padx=10, pady=5)
        adb_box.pack(side=tk.RIGHT, padx=20)
        tk.Label(adb_box, textvariable=self.adb_status_text, font=("Consolas", 9, "bold"), bg="#37474f", fg="#00e676").pack(side=tk.LEFT)
        tk.Button(adb_box, text="🔄 SYNC", font=("Segoe UI", 8, "bold"), bg="#455a64", fg="white", command=self.pull_latest_adb).pack(side=tk.LEFT, padx=(10, 0))

        instr_frame = tk.Frame(self.root, bg="#f5f5f5")
        instr_frame.pack(fill=tk.X, padx=25, pady=(10, 5))
        tk.Label(instr_frame, text="Fill in fields to set phone. Pair normally only needs to do when initially configuring the phone to the PC.", font=("Segoe UI", 10, "italic", "bold"), bg="#f5f5f5", fg="#d32f2f").pack(anchor="w")

        self.grid_container = tk.Frame(self.root, bg="#f5f5f5")
        self.grid_container.pack(pady=5, padx=25, fill=tk.X)
        self.render_device_grid()

        save_frame = tk.Frame(self.root, bg="#f5f5f5")
        save_frame.pack(fill=tk.X, padx=25, pady=10)
        tk.Button(save_frame, text="💾 SAVE IP/PORT TO JSON", bg="#1976d2", fg="white", font=("Segoe UI", 10, "bold"), height=2, command=self.save_all_changes).pack(fill=tk.X)

        maint_frame = tk.LabelFrame(self.root, text=" Maintenance ", bg="#f5f5f5")
        maint_frame.pack(pady=5, padx=25, fill=tk.X)
        tk.Button(maint_frame, text="☢️ ADB PURGE", bg="#c62828", fg="white", font=("Segoe UI", 9, "bold"), command=self.system_purge).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        tk.Button(maint_frame, text="🧹 CLEAR GHOSTS", bg="#b0bec5", fg="#263238", font=("Segoe UI", 9, "bold"), command=self.clear_ghosts).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        self.log_area = scrolledtext.ScrolledText(self.root, height=10, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10))
        self.log_area.pack(pady=(10, 15), padx=25, fill=tk.BOTH, expand=True)

    def render_device_grid(self):
        for widget in self.grid_container.winfo_children(): widget.destroy()
        self.entry_map = {}
        headers = [("Launch", "Launch"), ("Device Name", "Device Name"), ("Main IP", "Main IP"), ("Port", "Main Port"), ("Action", "Action"), ("Pair Address (IP:Port)", "Pairing Address"), ("Code", "6-Digit Code")]
        for i, (display_text, key) in enumerate(headers):
            nudge = HEADER_NUDGE.get(key, 0)
            tk.Label(self.grid_container, text=display_text, width=COL_WIDTHS[i], anchor="w", bg="#f5f5f5", font=("Segoe UI", 9, "bold")).grid(row=0, column=i, padx=(2 + nudge, 2), pady=(0, 5))

        for row_idx, (name, info) in enumerate(self.devices.items(), start=1):
            btn_color = info.get('button_color', '#757575')
            btn = tk.Button(self.grid_container, text="LAUNCH", width=COL_WIDTHS[0]-1, bg=btn_color, fg="white", font=("Segoe UI", 8, "bold"), command=lambda n=name: self.handle_toggle(n))
            btn.grid(row=row_idx, column=0, padx=2, pady=2)
            name_ent = tk.Entry(self.grid_container, width=COL_WIDTHS[1]-1); name_ent.insert(0, name); name_ent.grid(row=row_idx, column=1, padx=2)
            ip_ent = tk.Entry(self.grid_container, width=COL_WIDTHS[2]-1, bg="#e0f2f1"); ip_ent.insert(0, info.get('ip', '')); ip_ent.grid(row=row_idx, column=2, padx=2)
            port_ent = tk.Entry(self.grid_container, width=COL_WIDTHS[3]-1, bg="#fff9c4", justify=tk.CENTER); port_ent.insert(0, info.get('last_port', '')); port_ent.grid(row=row_idx, column=3, padx=2)
            p_btn = tk.Button(self.grid_container, text="PAIR", width=COL_WIDTHS[4]-1, bg="#000000", fg="#ffffff", font=("Segoe UI", 8, "bold"), command=lambda n=name: self.run_pairing(n))
            p_btn.grid(row=row_idx, column=4, padx=2)
            p_addr_ent = tk.Entry(self.grid_container, width=COL_WIDTHS[5]-1, bg="#fce4ec"); p_addr_ent.insert(0, f"{info.get('ip', '')}:"); p_addr_ent.grid(row=row_idx, column=5, padx=2)
            p_code_ent = tk.Entry(self.grid_container, width=COL_WIDTHS[6]-1, bg="#fce4ec", justify=tk.CENTER); p_code_ent.grid(row=row_idx, column=6, padx=2)
            self.entry_map[name] = {'ip': ip_ent, 'port': port_ent, 'btn': btn, 'p_addr': p_addr_ent, 'p_code': p_code_ent, 'orig_color': btn_color}
        self.update_button_labels()

    def run_pairing(self, name):
        widgets = self.entry_map[name]
        pair_address, code = widgets['p_addr'].get().strip(), widgets['p_code'].get().strip()
        if not pair_address or not code:
            messagebox.showwarning("Incomplete", "Enter Pairing Address and Code.")
            return
        def task():
            try:
                self.log(f"Pairing {name}...")
                proc = subprocess.Popen([LOCAL_ADB, "pair", pair_address], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW)
                stdout, stderr = proc.communicate(input=code, timeout=15)
                if "Successfully paired" in stdout:
                    self.log(f"SUCCESS: {name} paired!")
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"{name} Paired."))
                    widgets['p_code'].delete(0, tk.END)
                else: self.log(f"FAILED: {stdout} {stderr}")
            except Exception as e: self.log(f"Error: {e}")
        threading.Thread(target=task).start()

    def system_purge(self):
        subprocess.run("taskkill /F /IM adb.exe /T", shell=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(1)
        if os.path.exists(LOCAL_ADB): subprocess.run([LOCAL_ADB, "start-server"], capture_output=True, creationflags=CREATE_NO_WINDOW)

    def clear_ghosts(self):
        subprocess.run([LOCAL_ADB, "disconnect"], capture_output=True, creationflags=CREATE_NO_WINDOW)
        subprocess.run([LOCAL_ADB, "kill-server"], capture_output=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(1)
        subprocess.run([LOCAL_ADB, "start-server"], capture_output=True, creationflags=CREATE_NO_WINDOW)
        self.connected_ips.clear()
        self.update_button_labels()

    def log(self, message):
        self.log_area.insert(tk.END, f"> {message}\n"); self.log_area.see(tk.END)

    def status_monitor(self):
        while True:
            if self.monitor_active and os.path.exists(LOCAL_ADB):
                try:
                    res = subprocess.run([LOCAL_ADB, "devices"], capture_output=True, text=True, timeout=3, creationflags=CREATE_NO_WINDOW)
                    online = {line.split('\t')[0].split(':')[0] for line in res.stdout.strip().split('\n')[1:] if "\tdevice" in line}
                    if online != self.connected_ips:
                        self.connected_ips = online
                        self.root.after(0, self.update_button_labels)
                except: pass
            time.sleep(2)

    def update_button_labels(self):
        for name, widgets in self.entry_map.items():
            ip = widgets['ip'].get().strip()
            if ip in self.connected_ips: widgets['btn'].config(text="DISCONNECT", bg="#d32f2f") 
            else: widgets['btn'].config(text="LAUNCH", bg=widgets['orig_color'])

    # FIX: Modified to disconnect ALL active connections before launching a new one
    def handle_toggle(self, name):
        widgets = self.entry_map[name]
        ip, port = widgets['ip'].get().strip(), widgets['port'].get().strip()
        target = f"{ip}:{port}"

        # If user clicks the currently active phone, just disconnect it
        if ip in self.connected_ips:
            subprocess.run([LOCAL_ADB, "disconnect", target], capture_output=True, creationflags=CREATE_NO_WINDOW)
            return

        # NEW LOGIC: If a DIFFERENT phone is active, clear it first
        if self.connected_ips:
            self.log("Switching devices: Clearing existing active connections...")
            subprocess.run([LOCAL_ADB, "disconnect"], capture_output=True, creationflags=CREATE_NO_WINDOW)
            # Short pause to let ADB settle
            time.sleep(0.3)

        def task_conn():
            self.log(f"Connecting to {target}...")
            res = subprocess.run([LOCAL_ADB, "connect", target], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            if "connected" in res.stdout.lower():
                time.sleep(0.5)
                args = self.devices.get(name, {}).get("args", "")
                subprocess.Popen(f'start /b scrcpy -s {target} --window-title "{name}" {args}', shell=True, creationflags=CREATE_NO_WINDOW)
            else: self.log(f"FAILED: {res.stdout.strip()}")
        threading.Thread(target=task_conn).start()

    def safe_exit(self):
        if os.path.exists(LOCAL_ADB): 
            subprocess.run("taskkill /F /IM adb.exe /T", shell=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk(); app = AndroidManager(root); root.mainloop()