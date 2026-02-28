import tkinter as tk
from tkinter import messagebox, colorchooser
import json
import os
import shutil
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
CONFIG_FILE = "devices_config.json"

class DeviceAdder:
    def __init__(self, root):
        self.root = root
        self.root.title("Win2Phone - Device Manager")
        self.root.geometry("520x750")
        self.root.configure(bg="#f5f5f5")

        self.devices = self.load_config()
        # Keep track of the 'original' name when a device is selected for editing
        self.editing_original_name = None 
        self.selected_device_name = tk.StringVar(value="-- Select or Add New --")
        
        self.create_widgets()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def create_backup(self):
        if os.path.exists(CONFIG_FILE):
            timestamp = datetime.now().strftime("%y-%m-%d-%H%M%S")
            backup_name = f"{timestamp}.json"
            try:
                shutil.copy2(CONFIG_FILE, backup_name)
                return backup_name
            except:
                pass
        return None

    def save_config(self):
        backup_file = self.create_backup()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.devices, f, indent=4)
        
        msg = "JSON file updated successfully!"
        if backup_file:
            msg += f"\nBackup created: {backup_file}"
        messagebox.showinfo("Success", msg)
        self.refresh_dropdown()

    def create_widgets(self):
        header = tk.Frame(self.root, bg="#263238", height=60)
        header.pack(fill=tk.X)
        tk.Label(header, text="DEVICE CONFIG BUILDER", font=("Segoe UI", 12, "bold"), bg="#263238", fg="white").pack(pady=15)

        select_frame = tk.Frame(self.root, bg="#f5f5f5", pady=15)
        select_frame.pack(fill=tk.X, padx=30)
        
        tk.Label(select_frame, text="Current Phones:", bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.device_menu = tk.OptionMenu(select_frame, self.selected_device_name, *self.get_device_list(), command=self.populate_fields)
        self.device_menu.config(bg="white", relief=tk.GROOVE)
        self.device_menu.pack(fill=tk.X, pady=5)

        input_frame = tk.Frame(self.root, bg="#f5f5f5")
        input_frame.pack(fill=tk.BOTH, padx=30, expand=True)

        self.fields = {}
        field_configs = [
            ("Phone Name", "name", "Type over text (e.g. Pixel 8)"),
            ("Phone IP", "ip", "Type over text (e.g. 192.168.68.100)"),
            ("Last Port (Optional)", "last_port", "Leave blank or 5-digit port"),
            ("Scrcpy Args", "args", "--video-bit-rate 8M --stay-awake")
        ]

        for label, key, placeholder in field_configs:
            tk.Label(input_frame, text=label, bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
            ent = tk.Entry(input_frame, font=("Segoe UI", 10), bg="white", borderwidth=1, relief=tk.SOLID)
            ent.insert(0, placeholder)
            ent.pack(fill=tk.X, pady=2)
            self.fields[key] = ent

        tk.Label(input_frame, text="Button Color", bg="#f5f5f5", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.color_preview = tk.Label(input_frame, text="Click to Pick Color", bg="#757575", fg="white", cursor="hand2", pady=8)
        self.color_preview.pack(fill=tk.X, pady=2)
        self.color_preview.bind("<Button-1>", self.choose_color)
        self.current_color = "#757575"

        btn_frame = tk.Frame(self.root, bg="#f5f5f5", pady=20)
        btn_frame.pack(fill=tk.X, padx=30)

        tk.Button(btn_frame, text="💾 SAVE / UPDATE PHONE", bg="#2e7d32", fg="white", font=("Segoe UI", 10, "bold"), 
                  height=2, command=self.add_or_update).pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="🗑️ DELETE SELECTED", bg="#c62828", fg="white", command=self.delete_phone).pack(fill=tk.X)
        
        tk.Label(btn_frame, text="* Renaming an existing phone will overwrite the old entry.", 
                 bg="#f5f5f5", fg="#777", font=("Segoe UI", 8, "italic")).pack(pady=5)

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
            self.editing_original_name = name # Store the key we are currently editing
            dev = self.devices[name]
            self.clear_fields()
            self.fields["name"].insert(0, name)
            self.fields["ip"].insert(0, dev.get("ip", ""))
            self.fields["last_port"].insert(0, dev.get("last_port", ""))
            self.fields["args"].insert(0, dev.get("args", ""))
            self.current_color = dev.get("button_color", "#757575")
            self.color_preview.config(bg=self.current_color, text=self.current_color)
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

        # RENAME/OVERWRITE LOGIC:
        # If we were editing a device and the name changed, delete the old entry first.
        if self.editing_original_name and self.editing_original_name != new_name:
            if self.editing_original_name in self.devices:
                del self.devices[self.editing_original_name]

        # Save the new/updated data
        self.devices[new_name] = {
            "ip": self.fields["ip"].get().strip(),
            "last_port": self.fields["last_port"].get().strip(),
            "button_color": self.current_color,
            "args": self.fields["args"].get().strip()
        }
        
        self.save_config()
        self.editing_original_name = new_name # Update tracker to the new name

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

if __name__ == "__main__":
    root = tk.Tk()
    app = DeviceAdder(root)
    root.mainloop()