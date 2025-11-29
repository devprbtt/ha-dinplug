import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import yaml
import os

class CSVToYAMLConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV to YAML Converter")
        self.root.geometry("650x650")
        
        self.csv_file_path = tk.StringVar()
        self.host_ip = tk.StringVar(value="192.168.5.30")  # Default IP
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="CSV to YAML Converter", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="CSV File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(file_frame, text="Select CSV File:").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Entry(file_frame, textvariable=self.csv_file_path, width=50).grid(
            row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(file_frame, text="Browse", 
                  command=self.browse_csv_file).grid(row=1, column=1)
        
        # Host IP section
        ip_frame = ttk.LabelFrame(main_frame, text="Connection Settings", padding="10")
        ip_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(ip_frame, text="Host IP:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(ip_frame, textvariable=self.host_ip, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Convert button
        ttk.Button(main_frame, text="Convert to YAML", 
                  command=self.convert_to_yaml).grid(row=3, column=0, columnspan=3, pady=20)
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Conversion Results", padding="10")
        results_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Text widget for displaying YAML
        self.yaml_text = tk.Text(results_frame, height=15, width=70)
        yaml_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.yaml_text.yview)
        self.yaml_text.configure(yscrollcommand=yaml_scrollbar.set)
        
        self.yaml_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        yaml_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Button frame for Save and Copy buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        # Save button
        self.save_button = ttk.Button(button_frame, text="Save YAML File", 
                                     command=self.save_yaml_file, state="disabled")
        self.save_button.grid(row=0, column=0, padx=(0, 10))
        
        # Copy button
        self.copy_button = ttk.Button(button_frame, text="Copy YAML", 
                                     command=self.copy_yaml, state="disabled")
        self.copy_button.grid(row=0, column=1)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        file_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
    def browse_csv_file(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.csv_file_path.set(file_path)
            
    def convert_to_yaml(self):
        if not self.csv_file_path.get():
            messagebox.showerror("Error", "Please select a CSV file first.")
            return
            
        if not self.host_ip.get():
            messagebox.showerror("Error", "Please enter a host IP address.")
            return
            
        try:
            with open(self.csv_file_path.get(), 'r', encoding='utf-8') as csv_file:
                csv_reader = csv.DictReader(csv_file)
                lights_list = []
                
                for row in csv_reader:
                    # Skip Keypad Button and Button entries
                    if row['Entity'] not in ['Switch', 'Dimmer']:
                        continue
                        
                    # Extract device and channel from Address (format: "107:8")
                    address_parts = row['Address'].split(':')
                    
                    # Convert to integers to avoid quotes in YAML
                    try:
                        device = int(address_parts[0])
                        channel = int(address_parts[1])
                    except ValueError:
                        # If conversion fails, keep as string but show warning
                        device = address_parts[0]
                        channel = address_parts[1]
                        
                    # Determine dimmer value
                    dimmer = row['Button Type'] == 'Dimmer'
                    
                    light_config = {
                        'name': row['Label'],
                        'device': device,
                        'channel': channel,
                        'dimmer': dimmer
                    }
                    
                    lights_list.append(light_config)
            
            # Create the final YAML structure
            yaml_structure = {
                'light': [{
                    'platform': 'dinplug',
                    'host': self.host_ip.get(),
                    'port': 23,
                    'lights': lights_list
                }]
            }
            
            yaml_output = yaml.dump(yaml_structure, default_flow_style=False, 
                                  allow_unicode=True, sort_keys=False)
            
            # Display YAML in text widget
            self.yaml_text.delete(1.0, tk.END)
            self.yaml_text.insert(1.0, yaml_output)
            
            # Enable save and copy buttons
            self.save_button.config(state="normal")
            self.copy_button.config(state="normal")
            
            messagebox.showinfo("Success", f"Converted {len(lights_list)} lights to YAML format!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to convert CSV file:\n{str(e)}")
            
    def save_yaml_file(self):
        if not self.yaml_text.get(1.0, tk.END).strip():
            messagebox.showerror("Error", "No YAML content to save.")
            return
            
        # Suggest a filename based on the CSV file
        csv_path = self.csv_file_path.get()
        if csv_path:
            base_name = os.path.splitext(csv_path)[0]
            suggested_name = base_name + ".yaml"
        else:
            suggested_name = "lights_config.yaml"
            
        file_path = filedialog.asksaveasfilename(
            title="Save YAML File",
            initialfile=os.path.basename(suggested_name),
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as yaml_file:
                    yaml_file.write(self.yaml_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"YAML file saved successfully!\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save YAML file:\n{str(e)}")
                
    def copy_yaml(self):
        yaml_content = self.yaml_text.get(1.0, tk.END).strip()
        if not yaml_content:
            messagebox.showwarning("Warning", "No YAML content to copy.")
            return
            
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(yaml_content)
            self.root.update()  # Keep the clipboard content after the program exits
            messagebox.showinfo("Success", "YAML content copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard:\n{str(e)}")

def main():
    root = tk.Tk()
    app = CSVToYAMLConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()