import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
import random
import math
import keyboard
import json
import os
import pystray
from PIL import Image, ImageDraw
from pynput.mouse import Controller, Button
from tkinter.colorchooser import askcolor
import concurrent.futures

mouse_controller = Controller()

#shared settings
clicking = False
toggled = False
click_button = Button.left
current_mode = "Rage"  #track current mode
stop_threads = False

#rage Settings
rage_cps = 100  # Increased default CPS
rage_burst = 5
rage_jitter = 0.1
rage_burst_mode = "Fixed"     # Fixed/Random/Wave
min_burst = 1                 # Minimum bursts for random mode
max_burst = 10                # Maximum bursts for random mode
wave_peak = 10                # Peak bursts for wave mode
turbo_mode = False           # New turbo mode for extreme CPS

#legit Settings
legit_min_cps = 8
legit_max_cps = 12
legit_variance = 15
legit_click_style = "Normal"  # Normal/Butterfly/Jitter/Randomized
butterfly_delay = 0.05        # Delay between clicks in butterfly mode
jitter_intensity = 2          # Pixels of mouse jitter
random_pause_chance = 5       # 1-100% chance to pause
random_pause_duration = (0.1, 0.3)  # Range for random pauses

#configuration
hold_key = 'e'
toggle_key = 'f6'
toggle_mode = 'hold'  #hold/toggle
minimize_to_tray = True
always_on_top = False
thread_count = 2      # Number of clicking threads for higher performance

#appearance
color_theme = "light"
color_palettes = {
    "light": {"bg": "#ffffff", "fg": "#000000", "accent": "#0078d7"},
    "dark": {"bg": "#2a2a2a", "fg": "#000000", "accent": "#0078d7"},
    "custom": {"bg": "#ffffff", "fg": "#000000", "accent": "#0078d7"}
}

#stats tracking
total_clicks = 0
session_start_time = None
session_clicks = 0
auto_save_stats = True
click_times = []  # Store recent click times for accurate CPS calculation
max_click_times = 100  # Maximum number of click times to store

# Thread pool for parallel clicking
executor = None

def load_settings():
    global legit_click_style, butterfly_delay, jitter_intensity, random_pause_chance, random_pause_duration
    global rage_burst_mode, min_burst, max_burst, wave_peak, thread_count, turbo_mode
    
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
            # Add new settings to apply
            # Legit
            legit_click_style = legit_style_combo.get()
            butterfly_delay = float(butterfly_delay_entry.get())
            jitter_intensity = int(jitter_intensity_entry.get())
            random_pause_chance = int(pause_chance_entry.get())
            random_pause_duration = tuple(map(float, pause_duration_entry.get().split(',')))
            legit_click_style = data["legit"].get("click_style", "Normal")
            butterfly_delay = data["legit"].get("butterfly_delay", 0.05)
            jitter_intensity = data["legit"].get("jitter_intensity", 2)
            random_pause_chance = data["legit"].get("pause_chance", 5)
            random_pause_duration = tuple(data["legit"].get("pause_duration", (0.1, 0.3)))
            
            # Rage
            rage_burst_mode = rage_burst_combo.get()
            min_burst = int(min_burst_entry.get())
            max_burst = int(max_burst_entry.get())
            wave_peak = int(wave_peak_entry.get())
            rage_burst_mode = data["rage"].get("burst_mode", "Fixed")
            min_burst = data["rage"].get("min_burst", 1)
            max_burst = data["rage"].get("max_burst", 5)
            wave_peak = data["rage"].get("wave_peak", 5)
            turbo_mode = data["rage"].get("turbo_mode", False)
            
            # Performance settings
            thread_count = data.get("performance", {}).get("thread_count", 2)
                
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
            "rage_jitter": rage_jitter,
            "burst_mode": rage_burst_mode,
            "min_burst": min_burst,
            "max_burst": max_burst,
            "wave_peak": wave_peak,
            "turbo_mode": turbo_mode
        },
        "legit": {
            "legit_min_cps": legit_min_cps,
            "legit_max_cps": legit_max_cps,
            "legit_variance": legit_variance,
            "click_style": legit_click_style,
            "butterfly_delay": butterfly_delay,
            "jitter_intensity": jitter_intensity,
            "pause_chance": random_pause_chance,
            "pause_duration": random_pause_duration
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
        "performance": {
            "thread_count": thread_count
        },
        "current_mode": current_mode
    }
    try:
        with open("config.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        messagebox.showerror("Error", f"Could not save settings: {str(e)}")

def perform_click():
    """Execute a single click event"""
    global total_clicks, session_clicks, click_times
    
    mouse_controller.click(click_button)
    total_clicks += 1
    session_clicks += 1
    
    # Record click time for accurate CPS calculation
    current_time = time.time()
    click_times.append(current_time)
    if len(click_times) > max_click_times:
        click_times.pop(0)

def rage_clicker_worker():
    """Worker function for rage clicking mode"""
    global clicking, total_clicks, session_clicks, stop_threads
    burst_wave_counter = 0  # For wave burst mode

    while True:
        if stop_threads:
            break
        try:
            if clicking and current_mode == "Rage":
                # Calculate burst count based on mode
                if rage_burst_mode == "Fixed":
                    burst = rage_burst
                elif rage_burst_mode == "Random":
                    burst = random.randint(min_burst, max_burst)
                elif rage_burst_mode == "Wave":
                    burst = int((math.sin(burst_wave_counter) + 1) * wave_peak / 2)
                    burst_wave_counter += 0.5

                for _ in range(burst):
                    if stop_threads or not clicking:
                        break

                    perform_click()
                    update_stats_display()

                    # In turbo mode, reduce delay to minimum possible
                    if turbo_mode:
                        time.sleep(0.001)  # Absolute minimum delay
                    else:
                        jitter = 1 + random.uniform(-rage_jitter, rage_jitter)
                        time.sleep(max(0.001, (1 / rage_cps) * jitter))
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Error in rage clicker thread: {e}")
            time.sleep(0.1)

def legit_clicker_worker():
    """Worker function for legit clicking mode"""
    global clicking, total_clicks, session_clicks, stop_threads

    while True:
        if stop_threads:
            break
        try:
            if clicking and current_mode == "Legit":
                cps = random.uniform(legit_min_cps, legit_max_cps)
                variance = random.uniform(1 - legit_variance/100, 1 + legit_variance/100)
                delay = max(0.001, (1 / cps) * variance)

                # Random pause check
                if random.randint(1, 100) <= random_pause_chance:
                    pause_time = random.uniform(*random_pause_duration)
                    time.sleep(pause_time)

                if legit_click_style == "Butterfly":
                    perform_click()
                    time.sleep(butterfly_delay)
                    perform_click()
                    # Sleep for the rest of the interval so total = delay
                    remaining = delay - butterfly_delay
                    if remaining > 0:
                        time.sleep(remaining)
                elif legit_click_style == "Jitter":
                    original_pos = mouse_controller.position
                    jitter_x = original_pos[0] + random.randint(-jitter_intensity, jitter_intensity)
                    jitter_y = original_pos[1] + random.randint(-jitter_intensity, jitter_intensity)
                    mouse_controller.position = (jitter_x, jitter_y)
                    perform_click()
                    mouse_controller.position = original_pos
                    time.sleep(delay)
                else:
                    perform_click()
                    time.sleep(delay)

                update_stats_display()
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Error in legit clicker thread: {e}")
            time.sleep(0.1)
def clicker():
    """Main clicking function that distributes work to worker threads"""
    # This function now delegates to worker threads
    # We'll start worker threads from the main thread
    pass

def start_clicker_threads():
    """Start the appropriate number of clicking threads based on settings"""
    global executor, stop_threads

    # Signal old threads to stop
    stop_threads = True
    time.sleep(0.05)  # Give threads a moment to exit

    # Clean up existing executor if needed
    if executor is not None:
        executor.shutdown(wait=False)

    # Reset stop flag and start new threads
    stop_threads = False
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=thread_count)

    # Submit rage worker threads
    for _ in range(thread_count // 2 or 1):
        executor.submit(rage_clicker_worker)

    # Submit legit worker threads
    for _ in range(thread_count // 2 or 1):
        executor.submit(legit_clicker_worker)

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

def validate_legit_settings():
    try:
        min_cps = float(legit_min_entry.get())
        max_cps = float(legit_max_entry.get())
        variance = int(legit_variance_entry.get())
        
        if min_cps <= 0 or max_cps <= 0:
            raise ValueError("CPS values must be positive")
        if max_cps < min_cps:
            raise ValueError("Max CPS cannot be less than Min CPS")
        if variance < 0 or variance > 100:
            raise ValueError("Variance must be between 0-100%")
        
        return True
    except ValueError as e:
        messagebox.showerror("Invalid Settings", str(e))
        return False

def apply_settings(save=False):
    if not validate_legit_settings():
        return
    global current_mode, rage_cps, rage_burst, rage_jitter, turbo_mode
    global legit_min_cps, legit_max_cps, legit_variance
    global click_button, hold_key, toggle_key, toggle_mode
    global minimize_to_tray, always_on_top, auto_save_stats
    global thread_count
    
    try:
        #rage settings
        rage_cps = int(float(rage_cps_entry.get()))
        rage_burst = int(float(rage_burst_entry.get()))
        rage_jitter = float(rage_jitter_entry.get())
        turbo_mode = turbo_var.get()

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
        
        # Performance settings
        thread_count = int(thread_count_entry.get())
        
        current_mode = mode_switch.get()
        root.attributes('-topmost', always_on_top)
        
        # Restart clicking threads with new settings
        start_clicker_threads()
        
        #update ui
        update_status_indicator()
        
        if save:
            save_settings()
            messagebox.showinfo("Settings Saved", "Your settings have been saved successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Invalid settings: {str(e)}")

def calculate_current_cps():
    """Calculate actual CPS based on recent click times"""
    if len(click_times) < 2:
        return 0
    
    # Calculate time difference between oldest and newest click
    time_span = click_times[-1] - click_times[0]
    if time_span <= 0:
        return 0
    
    # Calculate clicks per second
    return (len(click_times) - 1) / time_span

def update_stats_display():
    if not hasattr(update_stats_display, "last_update") or time.time() - update_stats_display.last_update > 0.2:
        current_session_time = time.time() - session_start_time if session_start_time else 0
        hours, remainder = divmod(current_session_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        session_time_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        #calculate cps for this session
        current_cps = calculate_current_cps()
        
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
    global total_clicks, session_clicks, session_start_time, click_times
    
    if messagebox.askyesno("Reset Stats", "Are you sure you want to reset all statistics?"):
        total_clicks = 0
        session_clicks = 0
        session_start_time = time.time() if clicking else None
        click_times = []
        update_stats_display()
        save_settings()

def export_settings():
    try:
        with open("autoclicker_export.json", "w") as f:
            json.dump({
                "rage": {
                    "rage_cps": rage_cps,
                    "rage_burst": rage_burst,
                    "rage_jitter": rage_jitter,
                    "turbo_mode": turbo_mode
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
                },
                "performance": {
                    "thread_count": thread_count
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
                
                turbo_var.set(data["rage"].get("turbo_mode", False))
            
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
                
            # Import performance settings
            if "performance" in data:
                thread_count_entry.delete(0, tk.END)
                thread_count_entry.insert(0, str(data["performance"].get("thread_count", thread_count)))
        
        messagebox.showinfo("Import Successful", "Settings imported successfully!")
    except Exception as e:
        messagebox.showerror("Import Failed", f"Error: {str(e)}")

#gui yahuhuauhauh
root = tk.Tk()
root.title("Enhanced Auto Clicker")
root.geometry("640x580")  # Increased height for new options
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
performance_frame = ttk.Frame(tab_control)  # New performance tab

tab_control.add(rage_frame, text="Rage")
tab_control.add(legit_frame, text="Legit")
tab_control.add(config_frame, text="Config")
tab_control.add(appearance_frame, text="Appearance")
tab_control.add(stats_frame, text="Stats")
tab_control.add(performance_frame, text="Performance")  # Added performance tab
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

# Inside rage_frame grid
ttk.Label(rage_frame, text="Burst Mode:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
rage_burst_combo = ttk.Combobox(rage_frame, values=["Fixed", "Random", "Wave"], state="readonly")
rage_burst_combo.grid(row=3, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Min Burst:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
min_burst_entry = ttk.Entry(rage_frame)
min_burst_entry.grid(row=4, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Max Burst:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
max_burst_entry = ttk.Entry(rage_frame)
max_burst_entry.grid(row=5, column=1, padx=10, pady=5)

ttk.Label(rage_frame, text="Wave Peak:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
wave_peak_entry = ttk.Entry(rage_frame)
wave_peak_entry.grid(row=6, column=1, padx=10, pady=5)

# Turbo Mode Option
turbo_var = tk.BooleanVar(value=turbo_mode)
turbo_check = ttk.Checkbutton(rage_frame, text="Turbo Mode (Maximum CPS)", variable=turbo_var)
turbo_check.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")

# Turbo Mode Info
ttk.Label(rage_frame, text="Turbo Mode ignores CPS limits and clicks as fast as possible", 
          font=("Arial", 8, "italic")).grid(row=8, column=0, columnspan=2, padx=10, pady=0, sticky="w")

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
ttk.Label(legit_frame, text="Click Style:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
legit_style_combo = ttk.Combobox(legit_frame, values=["Normal", "Butterfly", "Jitter", "Randomized"], state="readonly")
legit_style_combo.grid(row=3, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Butterfly Delay (s):").grid(row=4, column=0, padx=10, pady=5, sticky="w")
butterfly_delay_entry = ttk.Entry(legit_frame)
butterfly_delay_entry.grid(row=4, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Jitter Intensity (px):").grid(row=5, column=0, padx=10, pady=5, sticky="w")
jitter_intensity_entry = ttk.Entry(legit_frame)
jitter_intensity_entry.grid(row=5, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Pause Chance (%):").grid(row=6, column=0, padx=10, pady=5, sticky="w")
pause_chance_entry = ttk.Entry(legit_frame)
pause_chance_entry.grid(row=6, column=1, padx=10, pady=5)

ttk.Label(legit_frame, text="Pause Duration (min,max):").grid(row=7, column=0, padx=10, pady=5, sticky="w")
pause_duration_entry = ttk.Entry(legit_frame)
pause_duration_entry.grid(row=7, column=1, padx=10, pady=5)

#config tab
ttk.Label(config_frame, text="Activation Key:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
hold_key_entry = ttk.Entry(config_frame, width=5)
hold_key_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

ttk.Label(config_frame, text="Toggle Key:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
toggle_key_entry = ttk.Entry(config_frame, width=5)
toggle_key_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")

ttk.Label(config_frame, text="Activation Mode:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
mode_choice = ttk.Combobox(config_frame, values=["hold", "toggle"], state="readonly", width=8)
mode_choice.grid(row=2, column=1, padx=10, pady=5, sticky="w")

ttk.Label(config_frame, text="Mouse Button:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
button_choice = ttk.Combobox(config_frame, values=["Left", "Right"], state="readonly", width=8)
button_choice.grid(row=3, column=1, padx=10, pady=5, sticky="w")

minimize_var = tk.BooleanVar(value=minimize_to_tray)
minimize_check = ttk.Checkbutton(config_frame, text="Minimize to Tray", variable=minimize_var)
minimize_check.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

always_top_var = tk.BooleanVar(value=always_on_top)
always_top_check = ttk.Checkbutton(config_frame, text="Always on Top", variable=always_top_var)
always_top_check.grid(row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w")

#appearance tab
theme_frame = ttk.LabelFrame(appearance_frame, text="Color Theme")
theme_frame.pack(padx=10, pady=5, fill=tk.X)

ttk.Radiobutton(theme_frame, text="Light", value="light", variable=color_theme, 
                command=lambda: change_theme("light")).pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(theme_frame, text="Dark", value="dark", variable=color_theme,
                command=lambda: change_theme("dark")).pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(theme_frame, text="Custom", value="custom", variable=color_theme,
                command=lambda: change_theme("custom")).pack(side=tk.LEFT, padx=5)

color_preview_frame = ttk.Frame(appearance_frame)
color_preview_frame.pack(padx=10, pady=5, fill=tk.X)

ttk.Label(color_preview_frame, text="Background:").pack(side=tk.LEFT, padx=5)
bg_preview = tk.Label(color_preview_frame, width=6, relief=tk.SUNKEN)
bg_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(color_preview_frame, text="Choose", 
          command=lambda: choose_custom_color("bg")).pack(side=tk.LEFT, padx=5)

ttk.Label(color_preview_frame, text="Text:").pack(side=tk.LEFT, padx=5)
fg_preview = tk.Label(color_preview_frame, width=6, relief=tk.SUNKEN)
fg_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(color_preview_frame, text="Choose",
          command=lambda: choose_custom_color("fg")).pack(side=tk.LEFT, padx=5)

ttk.Label(color_preview_frame, text="Accent:").pack(side=tk.LEFT, padx=5)
accent_preview = tk.Label(color_preview_frame, width=6, relief=tk.SUNKEN)
accent_preview.pack(side=tk.LEFT, padx=5)
ttk.Button(color_preview_frame, text="Choose",
          command=lambda: choose_custom_color("accent")).pack(side=tk.LEFT, padx=5)

#stats tab
stats_grid = ttk.Frame(stats_frame)
stats_grid.pack(padx=10, pady=10)

ttk.Label(stats_grid, text="Total Clicks:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
total_clicks_value = ttk.Label(stats_grid, text="0")
total_clicks_value.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(stats_grid, text="Session Clicks:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
session_clicks_value = ttk.Label(stats_grid, text="0")
session_clicks_value.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(stats_grid, text="Session Time:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
session_time_value = ttk.Label(stats_grid, text="00:00:00")
session_time_value.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(stats_grid, text="Current CPS:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
current_cps_value = ttk.Label(stats_grid, text="0.00")
current_cps_value.grid(row=3, column=1, padx=5, pady=5)

auto_save_var = tk.BooleanVar(value=auto_save_stats)
auto_save_check = ttk.Checkbutton(stats_frame, text="Auto-save Statistics", variable=auto_save_var)
auto_save_check.pack(pady=5)

reset_button = ttk.Button(stats_frame, text="Reset Statistics", command=reset_stats)
reset_button.pack(pady=5)

#performance tab
ttk.Label(performance_frame, text="Thread Count:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
thread_count_entry = ttk.Entry(performance_frame)
thread_count_entry.grid(row=0, column=1, padx=10, pady=5)

#control buttons
button_frame = ttk.Frame(root)
button_frame.pack(pady=10)

apply_button = ttk.Button(button_frame, text="Apply Settings", command=lambda: apply_settings())
apply_button.pack(side=tk.LEFT, padx=5)

save_button = ttk.Button(button_frame, text="Save", command=lambda: apply_settings(True))
save_button.pack(side=tk.LEFT, padx=5)

export_button = ttk.Button(button_frame, text="Export", command=export_settings)
export_button.pack(side=tk.LEFT, padx=5)

import_button = ttk.Button(button_frame, text="Import", command=import_settings)
import_button.pack(side=tk.LEFT, padx=5)

#initialize default values
rage_cps_entry.insert(0, str(rage_cps))
rage_burst_entry.insert(0, str(rage_burst))
rage_jitter_entry.insert(0, str(rage_jitter))
legit_min_entry.insert(0, str(legit_min_cps))
legit_max_entry.insert(0, str(legit_max_cps))
legit_variance_entry.insert(0, str(legit_variance))
butterfly_delay_entry.insert(0, str(butterfly_delay))
jitter_intensity_entry.insert(0, str(jitter_intensity))
pause_chance_entry.insert(0, str(random_pause_chance))
pause_duration_entry.insert(0, ",".join(map(str, random_pause_duration)))
hold_key_entry.insert(0, hold_key)
toggle_key_entry.insert(0, toggle_key)
mode_choice.set(toggle_mode)
button_choice.set("Left" if click_button == Button.left else "Right")
rage_burst_combo.set(rage_burst_mode)
min_burst_entry.insert(0, str(min_burst))
max_burst_entry.insert(0, str(max_burst))
wave_peak_entry.insert(0, str(wave_peak))
legit_style_combo.set(legit_click_style)
thread_count_entry.insert(0, str(thread_count))

#start threads
start_clicker_threads()
key_thread = threading.Thread(target=monitor_keys, daemon=True)
key_thread.start()

#apply theme and run
apply_theme()
update_color_preview()
root.mainloop()
