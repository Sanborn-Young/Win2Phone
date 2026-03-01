import tkinter as tk
from tkinter import messagebox, colorchooser
import json
import os
import shutil
import subprocess
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG_FILE = "devices_config.json"
ICON_FILE = "phone.ico" # Place a .ico file in the same folder to use it

class DeviceAdder:
    def __init__(self, root):
        self.root = root
        self.root.title("Win2Phone - Device Manager")
        self.root.geometry("520x1000")
        self.root.configure(bg="#f5f5f5")

        # Set Icon if exists
        if os.path.exists(ICON_FILE):
            try:
                self.root.iconbitmap(ICON_FILE)
            except:
                pass

        self.devices = self.load_config()
        self.editing_original_name = None 
        self.selected_device_name = tk.StringVar(value="-- Select or Add New --")
        self.always_on_top = tk.BooleanVar(value=False)
        
        self.create_widgets()
        self.log("System initialized. Ready.")

    def toggle_on_top(self):
        """Toggles the 'Always on Top' window state."""
        self.root.attributes("-topmost", self.always_on_top.get())
        status = "enabled" if self.always_on_top.get() else "disabled"
        self.log(f"Always on Top {status}.")

    def force_focus(self):
        """Brings the window to the front and grabs focus."""
        self.root.deiconify()
        self.root.focus_force()
        self.root.attributes("-topmost", True) # Momentarily force to front
        if not self.always_on_top.get():
            self.root.after(1000, lambda: self.root.attributes("-topmost", False))

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def log(self, message):
        """Appends a message to the activity log."""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def create_backup(self):
        if os.path.exists(CONFIG_FILE):
            timestamp = datetime.now().strftime("%y-%m-%d-%H%M%S")
            backup_name = f"{timestamp}.json"
            try:
                shutil.copy2(CONFIG_FILE, backup_name)
                self.log(f"Backup created: {backup_name}")
                return backup_name
            except Exception as e:
                self.log(f"Backup failed: {str(e)}")
        return None

    def save_config(self, quiet=False):
        backup_file = self.create_backup()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.devices, f, indent=4)
        
        if not quiet:
            messagebox.showinfo("Success", "JSON file updated successfully!")
        self.log("Configuration saved to JSON.")
        self.refresh_dropdown()

    def create_widgets(self):
        # HEADER with Toggle
        header = tk.Frame(self.root, bg="#263238", height=60)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="DEVICE CONFIG BUILDER", font=("Segoe UI", 12, "bold"), 
                 bg="#263238", fg="white").pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Checkbutton(header, text="Stay on Top", variable=self.always_on_top, 
                       command=self.toggle_on_top, bg="#263238", fg="white", 
                       selectcolor="#263238", activebackground="#263238", 
                       activeforeground="white").pack(side=tk.RIGHT, padx=20)

        # 1. SELECTION SECTION
        select_frame = tk.Frame(self.root, bg="#f5f5f5", pady=15)
        select_frame.pack(fill=tk.X, padx=30)
        
        tk.Label(select_frame, text="Current Phones (from JSON):", bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.device_menu = tk.OptionMenu(select_frame, self.selected_device_name, *self.get_device_list(), command=self.populate_fields)
        self.device_menu.config(bg="white", relief=tk.GROOVE)
        self.device_menu.pack(fill=tk.X, pady=5)

        # 2. INPUT FIELDS SECTION
        input_frame = tk.Frame(self.root, bg="#f5f5f5")
        input_frame.pack(fill=tk.X, padx=30)

        self.fields = {}
        field_configs = [
            ("Phone Name", "name", "Type over text (e.g. Pixel 8)"),
            ("Phone IP", "ip", "Type over text (e.g. 192.168.68.100)"),
            ("Last Port (Optional)", "last_port", "5555"),
            ("Scrcpy Args", "args", "--video-bit-rate 8M --stay-awake")
        ]

        for label, key, placeholder in field_configs:
            tk.Label(input_frame, text=label, bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))
            ent = tk.Entry(input_frame, font=("Segoe UI", 10), bg="white", borderwidth=1, relief=tk.SOLID)
            ent.insert(0, placeholder)
            ent.pack(fill=tk.X, pady=2)
            self.fields[key] = ent

        tk.Label(input_frame, text="Button Color", bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))
        self.color_preview = tk.Label(input_frame, text="Click to Pick Color", bg="#757575", fg="white", cursor="hand2", pady=8)
        self.color_preview.pack(fill=tk.X, pady=2)
        self.color_preview.bind("<Button-1>", self.choose_color)
        self.current_color = "#757575"

        # 3. BUILDER ACTION BUTTONS (Weighted 2/3 and 1/3)
        btn_frame = tk.Frame(self.root, bg="#f5f5f5", pady=15)
        btn_frame.pack(fill=tk.X, padx=30)
        
        btn_frame.columnconfigure(0, weight=2)
        btn_frame.columnconfigure(1, weight=1)

        tk.Button(btn_frame, text="💾 SAVE / UPDATE PHONE", bg="#2e7d32", fg="white", font=("Segoe UI", 10, "bold"), 
                  height=2, command=self.add_or_update).grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        tk.Button(btn_frame, text="🗑️ DELETE", bg="#c62828", fg="white", font=("Segoe UI", 10, "bold"),
                  command=self.delete_phone).grid(row=0, column=1, sticky="nsew")

        # 4. BLACK DISTINCTION BAR
        separator_bar = tk.Frame(self.root, bg="black", height=40)
        separator_bar.pack(fill=tk.X, pady=(10, 0))
        separator_bar.pack_propagate(False)
        tk.Label(separator_bar, text="Setting port at 5555 through USB", font=("Segoe UI", 10, "bold"), 
                 bg="black", fg="white").pack(pady=8)

        # 5. WIRELESS SETUP SECTION
        usb_frame = tk.Frame(self.root, bg="#e3f2fd", padx=20, pady=20)
        usb_frame.pack(fill=tk.X)

        instructions = "Step 1: Select phone above. Step 2: Plug USB & Set Port. Step 3: Connect Wi-Fi."
        tk.Label(usb_frame, text=instructions, bg="#e3f2fd", font=("Segoe UI", 8, "italic")).pack(pady=(0, 10))
        
        self.usb_btn = tk.Button(usb_frame, text="⚡ 1. SET PHONE TO PORT 5555 (USB)", bg="#0288d1", fg="white", 
                                font=("Segoe UI", 9, "bold"), height=2, command=self.run_usb_setup)
        self.usb_btn.pack(fill=tk.X, pady=2)

        self.wifi_btn = tk.Button(usb_frame, text="🌐 2. CONNECT VIA WI-FI", bg="#5e35b1", fg="white", 
                                 font=("Segoe UI", 9, "bold"), height=2, command=self.run_wifi_connect)
        self.wifi_btn.pack(fill=tk.X, pady=2)

        # 6. ACTIVITY LOG
        log_frame = tk.LabelFrame(self.root, text="Activity Log", bg="#f5f5f5", padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        log_frame.pack(fill=tk.BOTH, padx=30, pady=(10, 20), expand=True)

        self.log_text = tk.Text(log_frame, height=5, font=("Consolas", 9), bg="#eeeeee", state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def run_usb_setup(self):
        if not self.editing_original_name:
            self.log("ALERT: No phone selected from JSON.")
            messagebox.showwarning("Selection Required", "Please select a phone from the list above first.")
            return

        try:
            check_devices = subprocess.check_output(["adb", "devices"], stderr=subprocess.STDOUT, text=True)
            lines = [line.strip() for line in check_devices.strip().split('\n')[1:] if line.strip()]
            
            usb_serial = None
            for line in lines:
                if "device" in line and ":" not in line:
                    usb_serial = line.split()[0]
                    break
            
            if not usb_serial:
                 self.log("ERROR: No physical USB device found.")
                 self.force_focus() # Bring to front on error
                 messagebox.showerror("No USB Device", "No phone found via USB.")
                 return

            self.log(f"Targeting Serial: {usb_serial}")
            result = subprocess.check_output(["adb", "-s", usb_serial, "tcpip", "5555"], stderr=subprocess.STDOUT, text=True)
            self.log(result.strip())
            
            if "restarting in TCP mode" in result:
                self.fields["last_port"].delete(0, tk.END)
                self.fields["last_port"].insert(0, "5555")
                self.add_or_update()
                self.log("SUCCESS: Port 5555 active.")
                if messagebox.askyesno("Success", "Port 5555 set! Connect Wi-Fi now? (Unplug USB!)"):
                    self.run_wifi_connect()

        except Exception as e:
            self.log(f"ADB Error: {str(e)}")
            self.force_focus() # Alert user
            messagebox.showerror("ADB Error", str(e))

    def run_wifi_connect(self):
        if not self.editing_original_name:
            messagebox.showwarning("Selection Required", "Select a phone first.")
            return

        ip = self.fields["ip"].get().strip()
        port = self.fields["last_port"].get().strip() or "5555"
        target = f"{ip}:{port}"

        self.log(f"Connecting to {target}...")
        try:
            result = subprocess.check_output(["adb", "connect", target], stderr=subprocess.STDOUT, text=True)
            self.log(result.strip())
            if "connected to" in result:
                messagebox.showinfo("Wi-Fi Connected", f"Successfully linked to {target}")
            else:
                messagebox.showwarning("Status", result)
        except Exception as e:
            self.log(f"Failed: {str(e)}")
            self.force_focus()
            messagebox.showerror("Connection Failed", str(e))

    def get_device_list(self):
        lst = list(self.devices.keys())
        return lst if lst else ["-- No Devices Found --"]

    def refresh_dropdown(self):
        menu = self.device_menu["menu"]
        menu.delete(0, "end")
        for name in self.get_device_list():
            menu.add_command(label=name, command=lambda value=name: self.set_and_populate(value))

    def set_and_populate(self, value):
        self.selected_device_name.set(value)
        self.populate_fields(value)

    def populate_fields(self, name):
        if name in self.devices:
            self.editing_original_name = name 
            dev = self.devices[name]
            self.clear_fields()
            self.fields["name"].insert(0, name)
            self.fields["ip"].insert(0, dev.get("ip", ""))
            self.fields["last_port"].insert(0, dev.get("last_port", "5555"))
            self.fields["args"].insert(0, dev.get("args", ""))
            self.current_color = dev.get("button_color", "#757575")
            self.color_preview.config(bg=self.current_color, text=self.current_color)
            self.log(f"Loaded config for '{name}'")
        else:
            self.editing_original_name = None

    def clear_fields(self):
        for ent in self.fields.values():
            ent.delete(0, tk.END)

    def choose_color(self, event):
        color = colorchooser.askcolor(title="Select Button Color")[1]
        if color:
            self.current_color = color
            self.color_preview.config(bg=color, text=color)

    def add_or_update(self):
        new_name = self.fields["name"].get().strip()
        if not new_name or "Type over" in new_name:
            messagebox.showerror("Error", "Please enter a valid Phone Name")
            return

        if self.editing_original_name and self.editing_original_name != new_name:
            if self.editing_original_name in self.devices:
                del self.devices[self.editing_original_name]

        self.devices[new_name] = {
            "ip": self.fields["ip"].get().strip(),
            "last_port": self.fields["last_port"].get().strip(),
            "button_color": self.current_color,
            "args": self.fields["args"].get().strip()
        }
        
        self.save_config()
        self.editing_original_name = new_name 

    def delete_phone(self):
        name = self.selected_device_name.get()
        if name in self.devices:
            if messagebox.askyesno("Confirm Deletion", f"Permanently delete {name}?"):
                self.create_backup()
                del self.devices[name]
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.devices, f, indent=4)
                self.selected_device_name.set("-- Select or Add New --")
                self.clear_fields()
                self.refresh_dropdown()
                self.editing_original_name = None
                self.log(f"Deleted device: {name}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DeviceAdder(root)
    root.mainloop()