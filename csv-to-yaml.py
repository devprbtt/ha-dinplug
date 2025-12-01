import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import yaml
import os


class CSVToYAMLConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV to YAML Converter")
        self.root.geometry("750x800")

        self.csv_file_path = tk.StringVar()
        self.host_ip = tk.StringVar(value="192.168.5.30")

        # Toggles for what to convert
        self.include_lights = tk.BooleanVar(value=True)
        self.include_shades = tk.BooleanVar(value=True)
        self.include_keypads = tk.BooleanVar(value=True)
        self.include_buttons = tk.BooleanVar(value=True)

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        title_label = ttk.Label(
            main_frame, text="CSV to YAML Converter", font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="CSV File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(file_frame, text="Select CSV File:").grid(row=0, column=0, sticky=tk.W)

        ttk.Entry(file_frame, textvariable=self.csv_file_path, width=50).grid(
            row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10)
        )
        ttk.Button(file_frame, text="Browse", command=self.browse_csv_file).grid(row=1, column=1)

        # Host IP section
        ip_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        ip_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(ip_frame, text="Host IP:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(ip_frame, textvariable=self.host_ip, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=(10, 0)
        )

        # Type selection
        type_frame = ttk.LabelFrame(main_frame, text="Entities to convert", padding="10")
        type_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Checkbutton(
            type_frame, text="Lights (Switch/Dimmer)", variable=self.include_lights
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        ttk.Checkbutton(
            type_frame, text="Shades/Covers", variable=self.include_shades
        ).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Checkbutton(
            type_frame, text="Keypad Buttons", variable=self.include_keypads
        ).grid(row=1, column=0, sticky=tk.W, padx=(0, 20), pady=(5, 0))
        ttk.Checkbutton(
            type_frame, text="Buttons (generic)", variable=self.include_buttons
        ).grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(5, 0))

        ttk.Button(
            main_frame, text="Convert to YAML", command=self.convert_to_yaml
        ).grid(row=4, column=0, columnspan=3, pady=20)

        # Results
        results_frame = ttk.LabelFrame(main_frame, text="Conversion Results", padding="10")
        results_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.yaml_text = tk.Text(results_frame, height=18, width=80)
        yaml_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.yaml_text.yview)
        self.yaml_text.configure(yscrollcommand=yaml_scrollbar.set)

        self.yaml_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        yaml_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=10)

        self.save_button = ttk.Button(
            button_frame, text="Save YAML File", command=self.save_yaml_file, state="disabled"
        )
        self.save_button.grid(row=0, column=0, padx=(0, 10))

        self.copy_button = ttk.Button(
            button_frame, text="Copy YAML", command=self.copy_yaml, state="disabled"
        )
        self.copy_button.grid(row=0, column=1)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        file_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

    def browse_csv_file(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.csv_file_path.set(file_path)

    def _parse_address(self, address: str):
        parts = address.split(":")
        if len(parts) != 2:
            return address, None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return parts[0], parts[1]

    def _categorize_row(self, row):
        entity = row.get("Entity", "").strip().lower()
        label = row.get("Label", "")
        button_type = row.get("Button Type", "").strip().lower()

        device, channel = self._parse_address(row.get("Address", "0:0"))

        shade_keywords = ["persiana", "cortina", "shade", "cover", "blind"]

        if entity in {"dimmer", "switch", "light"}:
            return "light", {
                "name": label,
                "device": device,
                "channel": channel,
                "dimmer": entity == "dimmer",
            }

        if entity in {"shade", "cover", "curtain", "blind", "persiana"}:
            return "shade", {"name": label, "device": device, "channel": channel}

        # Heuristic: switches named like shades
        if entity == "switch" and any(word.lower() in label.lower() for word in shade_keywords):
            return "shade", {"name": label, "device": device, "channel": channel}

        if entity == "keypad button":
            return "keypad", {"name": label, "device": device, "button": channel}

        if entity == "button":
            return "button", {"name": label, "device": device, "button": channel}

        return None, None

    def convert_to_yaml(self):
        if not self.csv_file_path.get():
            messagebox.showerror("Error", "Please select a CSV file first.")
            return

        if not self.host_ip.get():
            messagebox.showerror("Error", "Please enter a host IP address.")
            return

        if not any(
            [
                self.include_lights.get(),
                self.include_shades.get(),
                self.include_keypads.get(),
                self.include_buttons.get(),
            ]
        ):
            messagebox.showerror("Error", "Select at least one entity type to convert.")
            return

        lights_list = []
        shades_list = []
        button_sensors = []

        try:
            with open(self.csv_file_path.get(), "r", encoding="utf-8") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for row in csv_reader:
                    category, payload = self._categorize_row(row)
                    if category == "light" and self.include_lights.get():
                        lights_list.append(payload)
                    elif category == "shade" and self.include_shades.get():
                        shades_list.append(payload)
                    elif category == "keypad" and self.include_keypads.get():
                        button_sensors.append(payload)
                    elif category == "button" and self.include_buttons.get():
                        button_sensors.append(payload)

            yaml_structure = {}
            if lights_list:
                yaml_structure["light"] = [
                    {
                        "platform": "dinplug",
                        "host": self.host_ip.get(),
                        "port": 23,
                        "lights": lights_list,
                    }
                ]
            if shades_list:
                yaml_structure["cover"] = [
                    {
                        "platform": "dinplug",
                        "host": self.host_ip.get(),
                        "port": 23,
                        "covers": shades_list,
                    }
                ]
            if button_sensors:
                yaml_structure["sensor"] = [
                    {
                        "platform": "dinplug",
                        "host": self.host_ip.get(),
                        "port": 23,
                        "buttons": button_sensors,
                    }
                ]

            if not yaml_structure:
                messagebox.showwarning(
                    "No entries",
                    "No matching rows were found for the selected entity types.",
                )
                return

            yaml_output = yaml.dump(
                yaml_structure, default_flow_style=False, allow_unicode=True, sort_keys=False
            )

            self.yaml_text.delete(1.0, tk.END)
            self.yaml_text.insert(1.0, yaml_output)

            self.save_button.config(state="normal")
            self.copy_button.config(state="normal")

            messagebox.showinfo(
                "Success",
                f"Converted: lights={len(lights_list)}, shades={len(shades_list)}, buttons={len(button_sensors)}",
            )

        except Exception as err:
            messagebox.showerror("Error", f"Failed to convert CSV file:\n{err}")

    def save_yaml_file(self):
        if not self.yaml_text.get(1.0, tk.END).strip():
            messagebox.showerror("Error", "No YAML content to save.")
            return

        csv_path = self.csv_file_path.get()
        if csv_path:
            base_name = os.path.splitext(csv_path)[0]
            suggested_name = base_name + ".yaml"
        else:
            suggested_name = "dinplug_config.yaml"

        file_path = filedialog.asksaveasfilename(
            title="Save YAML File",
            initialfile=os.path.basename(suggested_name),
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as yaml_file:
                    yaml_file.write(self.yaml_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"YAML file saved successfully!\n{file_path}")
            except Exception as err:
                messagebox.showerror("Error", f"Failed to save YAML file:\n{err}")

    def copy_yaml(self):
        yaml_content = self.yaml_text.get(1.0, tk.END).strip()
        if not yaml_content:
            messagebox.showwarning("Warning", "No YAML content to copy.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(yaml_content)
            self.root.update()
            messagebox.showinfo("Success", "YAML content copied to clipboard!")
        except Exception as err:
            messagebox.showerror("Error", f"Failed to copy to clipboard:\n{err}")


def main():
    root = tk.Tk()
    app = CSVToYAMLConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
