import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
import random
import keyboard
import json
import os
import pystray
from PIL import Image, ImageDraw
from pynput.mouse import Controller, Button
from tkinter.colorchooser import askcolor

mouse_controller = Controller()

#shared settings
clicking = False
toggled = False
click_button = Button.left
current_mode = "Rage"  #track current mode

#rage Settings
rage_cps = 20
rage_burst = 3
rage_jitter = 0.1

#legit Settings
legit_min_cps = 8
legit_max_cps = 12
legit_variance = 15

#configuration
hold_key = 'e'
toggle_key = 'f6'
toggle_mode = 'hold'  #hold/toggle
minimize_to_tray = True
always_on_top = False

#appearance
color_theme = "light"
color_palettes = {
    "light": {"bg": "#ffffff", "fg": "#000000", "accent": "#0078d7"},
    "dark": {"bg": "#1e1e1e", "fg": "#ffffff", "accent": "#00a2ff"},
    "custom": {"bg": "#ffffff", "fg": "#000000", "accent": "#0078d7"}
}

#stats tracking
total_clicks = 0
session_start_time = None
session_clicks = 0
auto_save_stats = True

def load_settings():
    global rage_cps, rage_burst, rage_jitter, legit_min_cps, legit_max_cps, legit_variance
    global hold_key, toggle_key, toggle_mode, minimize_to_tray, always_on_top
    global click_button, current_mode, color_theme, auto_save_stats, total_clicks
    
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            #rage
            if "rage" in data:
                rage_cps = data["rage"].get("rage_cps", rage_cps)
                rage_burst = data["rage"].get("rage_burst", rage_burst)
                rage_jitter = data["rage"].get("rage_jitter", rage_jitter)
            
            #legit
            if "legit" in data:
                legit_min_cps = data["legit"].get("legit_min_cps", legit_min_cps)
                legit_max_cps = data["legit"].get("legit_max_cps", legit_max_cps)
                legit_variance = data["legit"].get("legit_variance", legit_variance)
            
            #config
            if "config" in data:
                hold_key = data["config"].get("hold_key", hold_key)
                toggle_key = data["config"].get("toggle_key", toggle_key)
                toggle_mode = data["config"].get("toggle_mode", toggle_mode)
                minimize_to_tray = data["config"].get("minimize_to_tray", minimize_to_tray)
                always_on_top = data["config"].get("always_on_top", always_on_top)
                click_button_str = data["config"].get("button", "Left")
                click_button = Button.left if click_button_str == "Left" else Button.right
            
            #appearance
            if "appearance" in data:
                color_theme = data["appearance"].get("color_theme", color_theme)
                if "custom_colors" in data["appearance"]:
                    color_palettes["custom"] = data["appearance"]["custom_colors"]
            
            #stats
            if "stats" in data:
                total_clicks = data["stats"].get("total_clicks", 0)
                auto_save_stats = data["stats"].get("auto_save_stats", True)
            
            current_mode = data.get("current_mode", current_mode)
    except Exception as e:
        print(f"Error loading settings: {e}")

def save_settings():
    data = {
        "rage": {
            "rage_cps": rage_cps,
            "rage_burst": rage_burst,
            "rage_jitter": rage_jitter
        },
        "legit": {
            "legit_min_cps": legit_min_cps,
            "legit_max_cps": legit_max_cps,
            "legit_variance": legit_variance
        },
        "config": {
            "hold_key": hold_key,
            "toggle_key": toggle_key,
            "toggle_mode": toggle_mode,
            "button": "Left" if click_button == Button.left else "Right",
            "minimize_to_tray": minimize_to_tray,
            "always_on_top": always_on_top
        },
        "appearance": {
            "color_theme": color_theme,
            "custom_colors": color_palettes["custom"]
        },
        "stats": {
            "total_clicks": total_clicks,
            "auto_save_stats": auto_save_stats
        },
        "current_mode": current_mode
    }
    try:
        with open("config.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        messagebox.showerror("Error", f"Could not save settings: {str(e)}")

def clicker():
    global clicking, total_clicks, session_clicks
    while True:
        try:
            if clicking:
                if current_mode == "Rage":
                    #rage clicking with burst and jitter
                    for _ in range(rage_burst):
                        if not clicking:  #check if we should stop mid-burst
                            break
                        mouse_controller.click(click_button)
                        total_clicks += 1
                        session_clicks += 1
                        if stats_frame:
                            update_stats_display()
                        jitter = 1 + random.uniform(-rage_jitter, rage_jitter)
                        time.sleep(max(0.001, (1 / rage_cps) * jitter))
                else:
                    #legit human-like clicking
                    cps = random.randint(legit_min_cps, legit_max_cps)
                    variance = random.uniform(1 - legit_variance/100, 1 + legit_variance/100)
                    mouse_controller.click(click_button)
                    total_clicks += 1
                    session_clicks += 1
                    if stats_frame:
                        update_stats_display()
                    time.sleep(max(0.001, (1 / cps) * variance))
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Error in clicker thread: {e}")
            time.sleep(0.1)

def monitor_keys():
    global clicking, toggled
    while True:
        try:
            if toggle_mode == 'toggle' and keyboard.is_pressed(toggle_key):
                toggled = not toggled
                update_status_indicator()
                time.sleep(0.5)  #prevent multiple toggles
            
            new_clicking_state = toggled if toggle_mode == 'toggle' else keyboard.is_pressed(hold_key)
            
            #if we're starting a new clicking session
            if not clicking and new_clicking_state:
                global session_start_time, session_clicks
                session_start_time = time.time()
                session_clicks = 0
            
            #update clicking state
            clicking = new_clicking_state
            update_status_indicator()
            
            time.sleep(0.01)
        except Exception as e:
            print(f"Error in key monitor thread: {e}")
            time.sleep(0.1)

def update_status_indicator():
    if status_indicator:
        status_indicator.config(
            background="#4CAF50" if clicking else "#F44336",
            text="ACTIVE" if clicking else "IDLE"
        )

def apply_theme():
    palette = color_palettes[color_theme]
    style = ttk.Style()
    
    #configure the theme
    style.configure("TFrame", background=palette["bg"])
    style.configure("TLabel", background=palette["bg"], foreground=palette["fg"])
    style.configure("TButton", background=palette["accent"], foreground=palette["fg"])
    style.configure("TCheckbutton", background=palette["bg"], foreground=palette["fg"])
    style.configure("TEntry", fieldbackground=palette["bg"], foreground=palette["fg"])
    style.configure("TNotebook", background=palette["bg"], foreground=palette["fg"])
    style.configure("TNotebook.Tab", background=palette["bg"], foreground=palette["fg"])
    
    #apply to root window
    root.configure(background=palette["bg"])
    
    #update status indicator colors (if it exists)
    if status_indicator:
        status_indicator.config(foreground=palette["fg"])

def choose_custom_color(color_type):
    current_color = color_palettes["custom"][color_type]
    new_color = askcolor(color=current_color)[1]
    if new_color:
        color_palettes["custom"][color_type] = new_color
        update_color_preview()
        if color_theme == "custom":
            apply_theme()

def update_color_preview():
    if bg_preview:
        bg_preview.config(background=color_palettes["custom"]["bg"])
    if fg_preview:
        fg_preview.config(background=color_palettes["custom"]["fg"])
    if accent_preview:
        accent_preview.config(background=color_palettes["custom"]["accent"])

def change_theme(theme_name):
    global color_theme
    color_theme = theme_name
    apply_theme()

def create_tray_icon():
    #create a tray icon
    icon_size = 64
    icon_image = Image.new('RGBA', (icon_size, icon_size), color=(0, 0, 0, 0))
    dc = ImageDraw.Draw(icon_image)
    dc.ellipse((0, 0, icon_size, icon_size), fill=(255, 0, 0))
    dc.ellipse((16, 16, icon_size-16, icon_size-16), fill=(0, 0, 0, 0))
    
    def on_exit(icon):
        icon.stop()
        root.after(0, root.destroy)
    
    def on_restore(icon):
        icon.stop()
        root.after(0, root.deiconify)
    
    menu = (
        pystray.MenuItem('Open', on_restore),
        pystray.MenuItem('Exit', on_exit)
    )
    
    icon = pystray.Icon("autoclicker", icon_image, "Ultimate Clicker Pro", menu)
    return icon

def hide_to_tray():
    if minimize_to_tray:
        root.withdraw()
        if not hasattr(hide_to_tray, "icon") or not hide_to_tray.icon:
            hide_to_tray.icon = create_tray_icon()
            threading.Thread(target=hide_to_tray.icon.run, daemon=True).start()
    else:
        root.iconify()

def apply_settings(save=False):
    global current_mode, rage_cps, rage_burst, rage_jitter
    global legit_min_cps, legit_max_cps, legit_variance
    global click_button, hold_key, toggle_key, toggle_mode
    global minimize_to_tray, always_on_top, auto_save_stats
    
    try:
        #rage settings
        rage_cps = int(float(rage_cps_entry.get()))
        rage_burst = int(float(rage_burst_entry.get()))
        rage_jitter = float(rage_jitter_entry.get())
        
        #legit settings
        legit_min_cps = int(float(legit_min_entry.get()))
        legit_max_cps = int(float(legit_max_entry.get()))
        legit_variance = int(float(legit_variance_entry.get()))
        
        #config settings
        click_button = Button.left if button_choice.get() == "Left" else Button.right
        hold_key = hold_key_entry.get().lower()
        toggle_key = toggle_key_entry.get().lower()
        toggle_mode = mode_choice.get()
        minimize_to_tray = minimize_var.get()
        always_on_top = always_top_var.get()
        auto_save_stats = auto_save_var.get()
        
        current_mode = mode_switch.get()
        root.attributes('-topmost', always_on_top)
        
        #update ui
        update_status_indicator()
        
        if save:
            save_settings()
            messagebox.showinfo("Settings Saved", "Your settings have been saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Invalid settings: {str(e)}")

def update_stats_display():
    if not hasattr(update_stats_display, "last_update") or time.time() - update_stats_display.last_update > 0.2:
        current_session_time = time.time() - session_start_time if session_start_time else 0
        hours, remainder = divmod(current_session_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        session_time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        #calculate cps for this session
        current_cps = session_clicks / current_session_time if current_session_time > 0 else 0
        
        #update labels
        total_clicks_value.config(text=str(total_clicks))
        session_clicks_value.config(text=str(session_clicks))
        session_time_value.config(text=session_time_str)
        current_cps_value.config(text=f"{current_cps:.2f}")
        
        #auto-save stats periodically
        if auto_save_stats and total_clicks > 0:
            save_settings()
        
        update_stats_display.last_update = time.time()

def reset_stats():
    global total_clicks, session_clicks, session_start_time
    
    if messagebox.askyesno("Reset Stats", "Are you sure you want to reset all statistics?"):
        total_clicks = 0
        session_clicks = 0
        session_start_time = time.time() if clicking else None
        update_stats_display()
        save_settings()

def export_settings():
    try:
        with open("autoclicker_export.json", "w") as f:
            json.dump({
                "rage": {
                    "rage_cps": rage_cps,
                    "rage_burst": rage_burst,
                    "rage_jitter": rage_jitter
                },
                "legit": {
                    "legit_min_cps": legit_min_cps,
                    "legit_max_cps": legit_max_cps,
                    "legit_variance": legit_variance
                },
                "config": {
                    "hold_key": hold_key,
                    "toggle_key": toggle_key,
                    "toggle_mode": toggle_mode,
                    "button": "Left" if click_button == Button.left else "Right"
                }
            }, f, indent=4)
        messagebox.showinfo("Export Successful", "Settings exported to autoclicker_export.json")
    except Exception as e:
        messagebox.showerror("Export Failed", f"Error: {str(e)}")

def import_settings():
    try:
        if not os.path.exists("autoclicker_export.json"):
            messagebox.showerror("Import Failed", "No exported settings file found.")
            return
            
        with open("autoclicker_export.json", "r") as f:
            data = json.load(f)
            
            #import rage settings
            if "rage" in data:
                rage_cps_entry.delete(0, tk.END)
                rage_cps_entry.insert(0, str(data["rage"].get("rage_cps", rage_cps)))
                
                rage_burst_entry.delete(0, tk.END)
                rage_burst_entry.insert(0, str(data["rage"].get("rage_burst", rage_burst)))
                
                rage_jitter_entry.delete(0, tk.END)
                rage_jitter_entry.insert(0, str(data["rage"].get("rage_jitter", rage_jitter)))
            
            #import legit settings
            if "legit" in data:
                legit_min_entry.delete(0, tk.END)
                legit_min_entry.insert(0, str(data["legit"].get("legit_min_cps", legit_min_cps)))
                
                legit_max_entry.delete(0, tk.END)
                legit_max_entry.insert(0, str(data["legit"].get("legit_max_cps", legit_max_cps)))
                
                legit_variance_entry.delete(0, tk.END)
                legit_variance_entry.insert(0, str(data["legit"].get("legit_variance", legit_variance)))
            
            #import config settings
            if "config" in data:
                hold_key_entry.delete(0, tk.END)
                hold_key_entry.insert(0, data["config"].get("hold_key", hold_key))
                
                toggle_key_entry.delete(0, tk.END)
                toggle_key_entry.insert(0, data["config"].get("toggle_key", toggle_key))
                
                mode_choice.set(data["config"].get("toggle_mode", toggle_mode))
                button_choice.set(data["config"].get("button", "Left"))
        
        messagebox.showinfo("Import Successful", "Settings imported successfully!")
    except Exception as e:
        messagebox.showerror("Import Failed", f"Error: {str(e)}")

#gui setup
root = tk.Tk()
root.title("Auto Clicker")
root.geometry("640x520")
root.protocol("WM_DELETE_WINDOW", hide_to_tray)

#create variables for placeholders
status_indicator = None
bg_preview = None
fg_preview = None
accent_preview = None
stats_frame = None
total_clicks_value = None
session_clicks_value = None
session_time_value = None
current_cps_value = None

#create status bar at the top
status_frame = tk.Frame(root)
status_frame.pack(fill=tk.X, pady=5)

#mode Switch
mode_label = ttk.Label(status_frame, text="Mode:")
mode_label.pack(side=tk.LEFT, padx=10)

mode_switch = ttk.Combobox(status_frame, values=["Rage", "Legit"], state="readonly", width=10)
mode_switch.pack(side=tk.LEFT, padx=5)
mode_switch.set(current_mode)

#status Indicator
status_indicator = tk.Label(status_frame, text="IDLE", relief=tk.SUNKEN, width=8, 
                            background="#F44336", foreground="white",
                            font=("Arial", 9, "bold"))
status_indicator.pack(side=tk.RIGHT, padx=10)

status_text = ttk.Label(status_frame, text="Status:")
status_text.pack(side=tk.RIGHT, padx=5)

#notebook
tab_control = ttk.Notebook(root)
rage_frame = ttk.Frame(tab_control)
legit_frame = ttk.Frame(tab_control)
config_frame = ttk.Frame(tab_control)
appearance_frame = ttk.Frame(tab_control)
stats_frame = ttk.Frame(tab_control)

tab_control.add(rage_frame, text="Rage")
tab_control.add(legit_frame, text="Legit")
tab_control.add(config_frame, text="Config")
tab_control.add(appearance_frame, text="Appearance")
tab_control.add(stats_frame, text="Stats")
tab_control.pack(expand=1, fill="both", padx=10, pady=5)

#rage tab
ttk.Label(rage_frame, text="CPS (Clicks Per Second):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
rage_cps_entry = ttk.Entry(rage_frame)
rage_cps_entry.grid(row=0, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Burst Count:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
rage_burst_entry = ttk.Entry(rage_frame)
rage_burst_entry.grid(row=1, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Jitter (0-1):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
rage_jitter_entry = ttk.Entry(rage_frame)
rage_jitter_entry.grid(row=2, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Rage mode is designed for high speed clicking\nwith configurable burst patterns.", 
          font=("Arial", 9, "italic")).grid(row=3, column=0, columnspan=2, pady=20)

#legit tab
ttk.Label(legit_frame, text="Min CPS:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
legit_min_entry = ttk.Entry(legit_frame)
legit_min_entry.grid(row=0, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Max CPS:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
legit_max_entry = ttk.Entry(legit_frame)
legit_max_entry.grid(row=1, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Variance (%):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
legit_variance_entry = ttk.Entry(legit_frame)
legit_variance_entry.grid(row=2, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Legit mode mimics human clicking patterns\nwith natural timing variations.",
          font=("Arial", 9, "italic")).grid(row=3, column=0, columnspan=2, pady=20)

#config Tab
ttk.Label(config_frame, text="Control Mode:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
mode_choice = ttk.Combobox(config_frame, values=["hold", "toggle"], state="readonly")
mode_choice.grid(row=0, column=1, padx=10, pady=5)

ttk.Label(config_frame, text="Mouse Button:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
button_choice = ttk.Combobox(config_frame, values=["Left", "Right"], state="readonly")
button_choice.grid(row=1, column=1, padx=10, pady=5)

ttk.Label(config_frame, text="Hold Key:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
hold_key_entry = ttk.Entry(config_frame)
hold_key_entry.grid(row=2, column=1, padx=10, pady=5)

ttk.Label(config_frame, text="Toggle Key:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
toggle_key_entry = ttk.Entry(config_frame)
toggle_key_entry.grid(row=3, column=1, padx=10, pady=5)

minimize_var = tk.BooleanVar()
ttk.Checkbutton(config_frame, text="Minimize to Tray", variable=minimize_var).grid(row=4, column=0, padx=10, pady=5, sticky="w")
always_top_var = tk.BooleanVar()
ttk.Checkbutton(config_frame, text="Always on Top", variable=always_top_var).grid(row=4, column=1, padx=10, pady=5, sticky="w")

#import/export buttons
ttk.Button(config_frame, text="Export Settings", command=export_settings).grid(row=5, column=0, pady=10)
ttk.Button(config_frame, text="Import Settings", command=import_settings).grid(row=5, column=1, pady=10)

#apply/save buttons
ttk.Button(config_frame, text="Apply", command=lambda: apply_settings()).grid(row=6, column=0, pady=10)
ttk.Button(config_frame, text="Save", command=lambda: apply_settings(True)).grid(row=6, column=1, pady=10)

#appearance tab
ttk.Label(appearance_frame, text="Theme Selection:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
theme_frame = ttk.Frame(appearance_frame)
theme_frame.grid(row=0, column=1, padx=10, pady=10)

light_button = ttk.Button(theme_frame, text="Light", command=lambda: change_theme("light"))
light_button.pack(side=tk.LEFT, padx=5)

dark_button = ttk.Button(theme_frame, text="Dark", command=lambda: change_theme("dark"))
dark_button.pack(side=tk.LEFT, padx=5)

custom_button = ttk.Button(theme_frame, text="Custom", command=lambda: change_theme("custom"))
custom_button.pack(side=tk.LEFT, padx=5)

#custom Colors
ttk.Label(appearance_frame, text="Custom Colors:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
custom_colors_frame = ttk.Frame(appearance_frame)
custom_colors_frame.grid(row=1, column=1, padx=10, pady=10)

#background color
bg_frame = ttk.Frame(custom_colors_frame)
bg_frame.pack(fill=tk.X, pady=5)
ttk.Label(bg_frame, text="Background:").pack(side=tk.LEFT)
bg_preview = tk.Label(bg_frame, width=3, height=1, borderwidth=1, relief="solid", background=color_palettes["custom"]["bg"])
bg_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(bg_frame, text="Choose", command=lambda: choose_custom_color("bg")).pack(side=tk.LEFT)

#foreground color
fg_frame = ttk.Frame(custom_colors_frame)
fg_frame.pack(fill=tk.X, pady=5)
ttk.Label(fg_frame, text="Text:").pack(side=tk.LEFT)
fg_preview = tk.Label(fg_frame, width=3, height=1, borderwidth=1, relief="solid", background=color_palettes["custom"]["fg"])
fg_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(fg_frame, text="Choose", command=lambda: choose_custom_color("fg")).pack(side=tk.LEFT)

#accent color
accent_frame = ttk.Frame(custom_colors_frame)
accent_frame.pack(fill=tk.X, pady=5)
ttk.Label(accent_frame, text="Accent:").pack(side=tk.LEFT)
accent_preview = tk.Label(accent_frame, width=3, height=1, borderwidth=1, relief="solid", background=color_palettes["custom"]["accent"])
accent_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(accent_frame, text="Choose", command=lambda: choose_custom_color("accent")).pack(side=tk.LEFT)

ttk.Button(appearance_frame, text="Save Theme", command=lambda: apply_settings(True)).grid(row=2, column=1, pady=20)

#stats Tab
stats_header = ttk.Frame(stats_frame)
stats_header.pack(fill=tk.X, pady=10)

ttk.Label(stats_header, text="Clicking Statistics", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)
auto_save_var = tk.BooleanVar(value=auto_save_stats)
ttk.Checkbutton(stats_header, text="Auto-save stats", variable=auto_save_var).pack(side=tk.RIGHT, padx=10)

#stats display
stats_display = ttk.Frame(stats_frame)
stats_display.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

#total clicks
total_row = ttk.Frame(stats_display)
total_row.pack(fill=tk.X, pady=5)
ttk.Label(total_row, text="Total Clicks:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
total_clicks_value = ttk.Label(total_row, text="0")
total_clicks_value.pack(side=tk.RIGHT)

#session clicks
session_row = ttk.Frame(stats_display)
session_row.pack(fill=tk.X, pady=5)
ttk.Label(session_row, text="Session Clicks:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
session_clicks_value = ttk.Label(session_row, text="0")
session_clicks_value.pack(side=tk.RIGHT)

#session time
time_row = ttk.Frame(stats_display)
time_row.pack(fill=tk.X, pady=5)
ttk.Label(time_row, text="Session Time:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
session_time_value = ttk.Label(time_row, text="00:00:00")
session_time_value.pack(side=tk.RIGHT)

#current CPS
cps_row = ttk.Frame(stats_display)
cps_row.pack(fill=tk.X, pady=5)
ttk.Label(cps_row, text="Current CPS:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
current_cps_value = ttk.Label(cps_row, text="0.00")
current_cps_value.pack(side=tk.RIGHT)

#reset button
reset_button = ttk.Button(stats_frame, text="Reset Statistics", command=reset_stats)
reset_button.pack(pady=20)

#action buttons at the bottom
action_frame = tk.Frame(root)
action_frame.pack(fill=tk.X, pady=10)

hotkey_info = ttk.Label(action_frame, text=f"Hotkeys: Hold={hold_key}, Toggle={toggle_key}")
hotkey_info.pack(side=tk.LEFT, padx=10)

apply_button = ttk.Button(action_frame, text="Apply All Settings", command=lambda: apply_settings())
apply_button.pack(side=tk.RIGHT, padx=10)
save_button = ttk.Button(action_frame,)
save_button = ttk.Button(action_frame, text="Save All Settings", command=lambda: apply_settings(True))
save_button.pack(side=tk.RIGHT, padx=5)

#set initial values
def populate_fields():
    #rage
    rage_cps_entry.delete(0, tk.END)
    rage_cps_entry.insert(0, str(rage_cps))
    
    rage_burst_entry.delete(0, tk.END)
    rage_burst_entry.insert(0, str(rage_burst))
    
    rage_jitter_entry.delete(0, tk.END)
    rage_jitter_entry.insert(0, str(rage_jitter))
    
    #legit
    legit_min_entry.delete(0, tk.END)
    legit_min_entry.insert(0, str(legit_min_cps))
    
    legit_max_entry.delete(0, tk.END)
    legit_max_entry.insert(0, str(legit_max_cps))
    
    legit_variance_entry.delete(0, tk.END)
    legit_variance_entry.insert(0, str(legit_variance))
    
    #config
    mode_choice.set(toggle_mode)
    button_choice.set("Left" if click_button == Button.left else "Right")
    
    hold_key_entry.delete(0, tk.END)
    hold_key_entry.insert(0, hold_key)
    
    toggle_key_entry.delete(0, tk.END)
    toggle_key_entry.insert(0, toggle_key)
    
    minimize_var.set(minimize_to_tray)
    always_top_var.set(always_on_top)
    auto_save_var.set(auto_save_stats)

    #update hotkey info
    hotkey_info.config(text=f"Hotkeys: Hold={hold_key}, Toggle={toggle_key}")
    
    #apply theme
    apply_theme()
    update_color_preview()
    update_status_indicator()
    
    #set window properties
    root.attributes('-topmost', always_on_top)

#key detection for hold/toggle keys
def key_recorder(entry):
    def record_key(e):
        if e.keysym.lower() not in ('return', 'escape'):
            entry.delete(0, tk.END)
            entry.insert(0, e.keysym.lower())
            return "break"  # Prevent default action
    return record_key

#bind key recording to entry fields
hold_key_entry.bind("<Key>", key_recorder(hold_key_entry))
toggle_key_entry.bind("<Key>", key_recorder(toggle_key_entry))

#initialization
load_settings()
populate_fields()

#start threads
clicker_thread = threading.Thread(target=clicker, daemon=True)
key_monitor_thread = threading.Thread(target=monitor_keys, daemon=True)
clicker_thread.start()
key_monitor_thread.start()

#main loop
root.mainloop()

if auto_save_stats:
    try:
        save_settings()
    except:
        pass
