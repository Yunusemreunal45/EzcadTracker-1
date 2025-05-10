#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EZCAD2 Automation Application - Main Entry Point

This application provides integration between Excel data and EZCAD2 laser marking
software through a specialized C# bridge component.
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from datetime import datetime
import threading
import queue
import time
import json

# Import our modules
from logger import LoggerSetup, LogPanel
from config_manager import ConfigManager
from excel_handler import ExcelHandler
from ezcad_bridge import EZCADBridge
from ezcad_integration import EZCADIntegration

def setup_exception_logging():
    """Setup global exception handler to log unhandled exceptions"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Log unhandled exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Let keyboard interrupts pass through
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        logger = logging.getLogger('EZCADAutomation')
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Show error message to user
        from tkinter import messagebox
        messagebox.showerror("Unexpected Error", 
                             f"An unexpected error occurred: {exc_value}\n\n"
                             "Please check the log file for details.")
    
    # Set the exception hook
    sys.excepthook = handle_exception

def check_requirements():
    """Check for required libraries and attempt to install if missing"""
    required_packages = ['pandas', 'watchdog', 'psutil']
    missing_packages = []
    
    # Check which packages are missing
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    # If there are missing packages, try to install them
    if missing_packages:
        import sys
        from tkinter import messagebox
        
        # Inform the user
        message = f"Missing required packages: {', '.join(missing_packages)}\n\n"
        message += "Would you like to install them now?"
        
        if messagebox.askyesno("Missing Dependencies", message):
            try:
                import subprocess
                
                # Create a subprocess to install the packages
                python_exe = sys.executable
                subprocess.check_call([
                    python_exe, '-m', 'pip', 'install', 
                    '--upgrade', 'pip'
                ])
                
                # Install each missing package
                for package in missing_packages:
                    print(f"Installing {package}...")
                    subprocess.check_call([
                        python_exe, '-m', 'pip', 'install', package
                    ])
                
                # Success message
                messagebox.showinfo(
                    "Installation Complete", 
                    "Required packages have been installed.\nThe application will now continue."
                )
                
                # Verify installation
                failed_imports = []
                for package in missing_packages:
                    try:
                        __import__(package)
                    except ImportError:
                        failed_imports.append(package)
                
                if failed_imports:
                    messagebox.showerror(
                        "Installation Failed", 
                        f"Failed to import these packages after installation: {', '.join(failed_imports)}\n"
                        "Please install them manually and restart the application."
                    )
                    return False
                
                return True
                
            except Exception as e:
                error_message = f"Failed to install packages: {str(e)}\n\n"
                error_message += "Please install them manually and restart the application:\n"
                error_message += f"pip install {' '.join(missing_packages)}"
                messagebox.showerror("Installation Error", error_message)
                return False
        else:
            # User chose not to install
            return False
    
    return True

class EZCADAutomationApp:
    """The main EZCAD Automation application"""
    
    def __init__(self, root):
        """Initialize the application"""
        self.root = root
        root.title("EZCAD2 Automation")
        root.geometry("900x700")
        
        # Initialize logger
        self.logger_setup = LoggerSetup()
        self.logger = self.logger_setup.get_logger()
        self.log_queue = self.logger_setup.get_queue()
        
        # Initialize config
        self.config = ConfigManager()
        
        # Initialize components
        self.excel_handler = ExcelHandler(self.logger)
        self.integration = EZCADIntegration(self.config, self.logger)
        
        # Setup the UI
        self._create_ui()
        
        # Refresh UI with loaded config
        self._refresh_from_config()
    
    def _create_ui(self):
        """Create the application UI"""
        # Create a notebook (tabbed interface)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create main tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main")
        self._create_main_tab(main_tab)
        
        # Create settings tab
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        self._create_settings_tab(settings_tab)
        
        # Create log tab
        log_tab = ttk.Frame(notebook)
        notebook.add(log_tab, text="Logs")
        self._create_log_tab(log_tab)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Clock label on right of status bar
        self.clock_var = tk.StringVar()
        clock_label = ttk.Label(status_frame, textvariable=self.clock_var)
        clock_label.pack(side=tk.RIGHT)
        
        # Start the clock update
        self._update_clock()
    
    def _create_main_tab(self, parent):
        """Create the main tab content"""
        # Files selection frame
        files_frame = ttk.LabelFrame(parent, text="Files")
        files_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Excel file
        ttk.Label(files_frame, text="Excel File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.excel_path_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.excel_path_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Browse", command=self._select_excel).grid(row=0, column=2, padx=5, pady=5)
        
        # EZD template file
        ttk.Label(files_frame, text="EZD Template:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ezd_path_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.ezd_path_var, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Browse", command=self._select_ezd).grid(row=1, column=2, padx=5, pady=5)
        
        # Bridge path
        ttk.Label(files_frame, text="Bridge EXE:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.bridge_exe_var = tk.StringVar()
        ttk.Entry(files_frame, textvariable=self.bridge_exe_var, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(files_frame, text="Browse", command=self._select_bridge_exe).grid(row=2, column=2, padx=5, pady=5)
        
        # Excel preview
        preview_frame = ttk.LabelFrame(parent, text="Excel Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=10)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_text.config(state=tk.DISABLED)
        
        # Template info frame
        template_frame = ttk.LabelFrame(parent, text="Template Entities")
        template_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.entities_text = scrolledtext.ScrolledText(template_frame, height=5)
        self.entities_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.entities_text.config(state=tk.DISABLED)
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.test_button = ttk.Button(control_frame, text="Test Bridge", command=self._test_bridge)
        self.test_button.pack(side=tk.LEFT, padx=5)
        
        self.list_button = ttk.Button(control_frame, text="List Entities", command=self._list_entities)
        self.list_button.pack(side=tk.LEFT, padx=5)
        
        self.process_button = ttk.Button(control_frame, text="Process Excel", command=self._process_excel)
        self.process_button.pack(side=tk.LEFT, padx=5)
    
    def _create_settings_tab(self, parent):
        """Create the settings tab content"""
        # General settings
        general_frame = ttk.LabelFrame(parent, text="General Settings")
        general_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Auto-update Excel status
        self.update_excel_status_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(general_frame, text="Update Excel Status After Processing", 
                      variable=self.update_excel_status_var).pack(anchor="w", padx=5, pady=5)
        
        # Output options
        output_frame = ttk.LabelFrame(parent, text="Output Options")
        output_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Auto-save output
        self.auto_save_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(output_frame, text="Auto-Save Modified Templates", 
                      variable=self.auto_save_var).pack(anchor="w", padx=5, pady=5)
        
        # Output directory
        ttk.Label(output_frame, text="Output Directory:").pack(anchor="w", padx=5, pady=5)
        output_dir_frame = ttk.Frame(output_frame)
        output_dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.output_dir_var = tk.StringVar()
        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(output_dir_frame, text="Browse", 
                 command=self._select_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Profiles
        profile_frame = ttk.LabelFrame(parent, text="Configuration Profiles")
        profile_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Profile controls
        profile_controls = ttk.Frame(profile_frame)
        profile_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(profile_controls, text="Profile Name:").pack(side=tk.LEFT, padx=5)
        
        self.profile_name_var = tk.StringVar()
        ttk.Entry(profile_controls, textvariable=self.profile_name_var, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(profile_controls, text="Save Profile", 
                 command=self._save_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(profile_controls, text="Load Profile", 
                 command=self._show_load_profile).pack(side=tk.LEFT, padx=5)
        
        # Save/Apply buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=(20, 10))
        
        ttk.Button(button_frame, text="Apply Settings", 
                 command=self._apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Default", 
                 command=self._reset_settings).pack(side=tk.RIGHT, padx=5)
    
    def _create_log_tab(self, parent):
        """Create the log tab content"""
        # Create the log panel
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_panel = LogPanel(log_frame, self.log_queue)
        
        # Log controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(controls_frame, text="Clear Log", 
                 command=self.log_panel.clear).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Open Log Directory", 
                 command=self._open_log_directory).pack(side=tk.LEFT, padx=5)
    
    def _update_clock(self):
        """Update the clock in the status bar"""
        self.clock_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._update_clock)
    
    def _refresh_from_config(self):
        """Refresh UI elements from the config"""
        # Files paths
        self.excel_path_var.set(self.config.get('Paths', 'last_excel_file', fallback=''))
        self.ezd_path_var.set(self.config.get('Integration', 'default_template', fallback=''))
        self.bridge_exe_var.set(self.config.get('Paths', 'ezcad_bridge_exe', fallback=''))
        
        # Settings
        self.update_excel_status_var.set(self.config.getboolean('Settings', 'update_excel_status', fallback=True))
        self.auto_save_var.set(self.config.getboolean('Integration', 'auto_save_output', fallback=False))
        self.output_dir_var.set(self.config.get('Integration', 'output_directory', fallback=''))
    
    def _apply_settings(self):
        """Apply settings from UI to config"""
        # File paths
        self.config.set('Paths', 'ezcad_bridge_exe', self.bridge_exe_var.get())
        self.config.set('Integration', 'default_template', self.ezd_path_var.get())
        
        # Settings
        self.config.set('Settings', 'update_excel_status', str(self.update_excel_status_var.get()))
        self.config.set('Integration', 'auto_save_output', str(self.auto_save_var.get()))
        self.config.set('Integration', 'output_directory', self.output_dir_var.get())
        
        # Save config
        self.config.save_config()
        
        self.logger.info("Settings applied and saved")
        messagebox.showinfo("Settings", "Settings have been applied and saved.")
    
    def _reset_settings(self):
        """Reset settings to default"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to default?"):
            self.config._create_default_config()
            self._refresh_from_config()
            self.logger.info("Settings reset to default")
            messagebox.showinfo("Settings", "Settings have been reset to default.")
    
    def _select_excel(self):
        """Browse for Excel file"""
        file_types = [("Excel files", "*.xls;*.xlsx"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(title="Select Excel File", filetypes=file_types)
        
        if file_path:
            self.excel_path_var.set(file_path)
            self.config.set('Paths', 'last_excel_file', file_path)
            last_dir = os.path.dirname(file_path)
            self.config.set('Paths', 'last_excel_dir', last_dir)
            self.config.save_config()
            
            # Load and preview
            df = self.excel_handler.load_excel(file_path)
            if df is not None:
                preview = self.excel_handler.get_preview()
                
                self.preview_text.config(state=tk.NORMAL)
                self.preview_text.delete("1.0", tk.END)
                self.preview_text.insert(tk.END, preview)
                self.preview_text.config(state=tk.DISABLED)
    
    def _select_ezd(self):
        """Browse for EZD file"""
        file_types = [("EZD files", "*.ezd"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(title="Select EZD Template File", filetypes=file_types)
        
        if file_path:
            self.ezd_path_var.set(file_path)
            self.config.set('Integration', 'default_template', file_path)
            last_dir = os.path.dirname(file_path)
            self.config.set('Paths', 'last_ezd_dir', last_dir)
            self.config.save_config()
            self.logger.info(f"Selected EZD template: {file_path}")
            
            # Try to list entities
            self._list_entities()
    
    def _select_bridge_exe(self):
        """Browse for bridge executable"""
        file_types = [("Executable files", "*.exe"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(title="Select EZCADBridge Executable", filetypes=file_types)
        
        if file_path:
            self.bridge_exe_var.set(file_path)
            self.config.set('Paths', 'ezcad_bridge_exe', file_path)
            self.config.save_config()
            self.logger.info(f"Selected bridge executable: {file_path}")
            
            # Reinitialize integration with new bridge path
            self.integration = EZCADIntegration(self.config, self.logger)
    
    def _select_output_dir(self):
        """Browse for output directory"""
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        
        if dir_path:
            self.output_dir_var.set(dir_path)
            self.config.set('Integration', 'output_directory', dir_path)
            self.config.save_config()
            self.logger.info(f"Selected output directory: {dir_path}")
    
    def _test_bridge(self):
        """Test the bridge connection"""
        ezd_file = self.ezd_path_var.get()
        if not ezd_file:
            messagebox.showwarning("Missing File", "Please select an EZD template file first.")
            return
        
        self.status_var.set("Testing bridge connection...")
        
        # Run test in a separate thread
        threading.Thread(target=self._test_bridge_thread, args=(ezd_file,), daemon=True).start()
    
    def _test_bridge_thread(self, ezd_file):
        """Thread function to test bridge"""
        try:
            result = self.integration.test_integration(ezd_file)
            
            if result:
                self.root.after(0, lambda: messagebox.showinfo("Bridge Test", "Bridge connection successful!"))
                self.root.after(0, lambda: self.status_var.set("Bridge connection successful"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Bridge Test", "Failed to connect to bridge."))
                self.root.after(0, lambda: self.status_var.set("Bridge connection failed"))
                
        except Exception as e:
            self.logger.error(f"Error in bridge test: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Bridge Error", f"Error: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("Error"))
    
    def _list_entities(self):
        """List entities in the current template"""
        ezd_file = self.ezd_path_var.get()
        if not ezd_file:
            messagebox.showwarning("Missing File", "Please select an EZD template file first.")
            return
        
        self.status_var.set("Listing template entities...")
        
        # Run in a separate thread
        threading.Thread(target=self._list_entities_thread, args=(ezd_file,), daemon=True).start()
    
    def _list_entities_thread(self, ezd_file):
        """Thread function to list entities"""
        try:
            entities = self.integration.list_entities_in_template(ezd_file)
            
            # Update entities display
            entities_text = "Template entities:\n"
            if entities:
                for entity in entities:
                    entities_text += f"  - {entity}\n"
            else:
                entities_text += "  No text entities found in template."
                
            self.root.after(0, lambda: self._update_entities_text(entities_text))
            self.root.after(0, lambda: self.status_var.set(f"Found {len(entities)} entities"))
                
        except Exception as e:
            self.logger.error(f"Error listing entities: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Entity List Error", f"Error: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("Error"))
    
    def _update_entities_text(self, text):
        """Update the entities text widget"""
        self.entities_text.config(state=tk.NORMAL)
        self.entities_text.delete("1.0", tk.END)
        self.entities_text.insert(tk.END, text)
        self.entities_text.config(state=tk.DISABLED)
    
    def _process_excel(self):
        """Process the Excel file with EZCAD"""
        excel_file = self.excel_path_var.get()
        ezd_file = self.ezd_path_var.get()
        
        if not excel_file:
            messagebox.showwarning("Missing File", "Please select an Excel file first.")
            return
            
        if not ezd_file:
            messagebox.showwarning("Missing File", "Please select an EZD template file first.")
            return
        
        # Determine output path if auto-save is enabled
        output_path = None
        if self.auto_save_var.get():
            output_dir = self.output_dir_var.get()
            if output_dir and os.path.exists(output_dir):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_basename = os.path.splitext(os.path.basename(ezd_file))[0]
                output_path = os.path.join(output_dir, f"{output_basename}_{timestamp}.ezd")
            else:
                messagebox.showwarning("Output Directory", 
                                     "Auto-save is enabled but output directory is not set or doesn't exist.")
                return
        
        self.status_var.set("Processing Excel file...")
        
        # Run processing in a separate thread
        threading.Thread(target=self._process_excel_thread, 
                       args=(excel_file, ezd_file, output_path), 
                       daemon=True).start()
    
    def _process_excel_thread(self, excel_file, ezd_file, output_path):
        """Thread function to process Excel"""
        try:
            # Apply current settings
            self.config.set('Settings', 'update_excel_status', str(self.update_excel_status_var.get()))
            
            # Process the file
            result = self.integration.process_excel_file(excel_file, ezd_file, output_path)
            
            # Show results
            if result.get('success', False):
                success_count = result.get('success', 0)
                total_count = result.get('total', 0)
                duration = result.get('duration', 0)
                
                message = f"Processing complete!\n\n"
                message += f"Successfully processed: {success_count}/{total_count} items\n"
                message += f"Duration: {duration:.2f} seconds"
                
                if output_path and os.path.exists(output_path):
                    message += f"\n\nOutput saved to: {output_path}"
                
                self.root.after(0, lambda: messagebox.showinfo("Processing Complete", message))
                self.root.after(0, lambda: self.status_var.set(f"Processed {success_count}/{total_count} items"))
            else:
                error_msg = result.get('error', 'Unknown error')
                self.root.after(0, lambda: messagebox.showerror("Processing Error", f"Error: {error_msg}"))
                self.root.after(0, lambda: self.status_var.set("Processing failed"))
                
        except Exception as e:
            self.logger.error(f"Error processing Excel: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Processing Error", f"Error: {str(e)}"))
            self.root.after(0, lambda: self.status_var.set("Error"))
    
    def _save_profile(self):
        """Save current settings as a profile"""
        profile_name = self.profile_name_var.get().strip()
        if not profile_name:
            messagebox.showwarning("Profile Name", "Please enter a profile name.")
            return
        
        try:
            # Apply current UI settings to config
            self._apply_settings()
            
            # Save profile
            profile_file = self.config.save_profile(profile_name)
            self.logger.info(f"Saved profile: {profile_name} to {profile_file}")
            messagebox.showinfo("Profile Saved", f"Profile '{profile_name}' has been saved.")
            
        except Exception as e:
            self.logger.error(f"Error saving profile: {str(e)}")
            messagebox.showerror("Profile Error", f"Error saving profile: {str(e)}")
    
    def _show_load_profile(self):
        """Show dialog to select a profile to load"""
        profiles = self.config.list_profiles()
        
        if not profiles:
            messagebox.showinfo("No Profiles", "No saved profiles found.")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Profile")
        dialog.geometry("300x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Select a profile to load:").pack(padx=10, pady=10)
        
        # Create listbox
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        listbox = tk.Listbox(listbox_frame)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for profile in profiles:
            listbox.insert(tk.END, profile)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Load", 
                 command=lambda: self._load_selected_profile(listbox, dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", 
                 command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _load_selected_profile(self, listbox, dialog):
        """Load the selected profile"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a profile to load.")
            return
        
        profile_name = listbox.get(selection[0])
        
        try:
            self.config.load_profile(profile_name)
            self.logger.info(f"Loaded profile: {profile_name}")
            
            # Refresh UI
            self._refresh_from_config()
            
            # Close dialog
            dialog.destroy()
            
            messagebox.showinfo("Profile Loaded", f"Profile '{profile_name}' has been loaded.")
            
        except Exception as e:
            self.logger.error(f"Error loading profile: {str(e)}")
            messagebox.showerror("Profile Error", f"Error loading profile: {str(e)}")
    
    def _open_log_directory(self):
        """Open the log directory in file explorer"""
        log_dir = os.path.abspath("logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Open file explorer to log directory
        if sys.platform == 'win32':
            os.startfile(log_dir)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', log_dir])
    
    def on_closing(self):
        """Handle window closing"""
        # Cleanup
        if hasattr(self, 'log_panel'):
            self.log_panel.stop()
        
        # Close the window
        self.root.destroy()


def main():
    """Main entry point for the application"""
    # Set up exception logging
    setup_exception_logging()
    
    # Check for required dependencies
    if not check_requirements():
        return
    
    # Create the main window
    root = tk.Tk()
    
    # Set icon (optional)
    try:
        root.iconbitmap("generated-icon.png")
    except:
        pass  # No icon available, continue without
    
    # Create the application
    app = EZCADAutomationApp(root)
    
    # Set up the window close handler
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the main loop
    root.mainloop()


if __name__ == "__main__":
    main()