import speech_recognition as sr
import os
import platform
import subprocess
import pyttsx3
import psutil
import datetime
import webbrowser
import random
import shutil
import time
import threading
import json
import requests
import math
from deep_translator import GoogleTranslator
from calendar import monthcalendar, month_name
import socket
import glob
import difflib  # For fuzzy matching

# =========================
# Configuration
# =========================
CONFIG_FILE = os.path.expanduser("~/.voice_agent_config.json")
MEMORY_FILE = os.path.expanduser("~/.voice_agent_memory.json")
NOTES_FILE = os.path.expanduser("~/Documents/agent_notes.txt")

# Weather API configuration - using free alternative (Open-Meteo)
WEATHER_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Track opened applications
opened_apps = {}

# =========================
# Speech: Initialize engine with better voice selection
# =========================
def init_tts_engine():
    """Initialize text-to-speech engine with better voice selection"""
    engine = pyttsx3.init()
    engine.setProperty('rate', 230)
    engine.setProperty('volume', 1.0)
    
    voices = engine.getProperty('voices')
    
    # Prioritize high-quality voices
    preferred_voices = [
        # "samantha",     # macOS high-quality voice
        "alex"         # macOS high-quality voice
        # "Karen",        # macOS Australian English
        # "Daniel",       # macOS British English
        # "Microsoft David Desktop",  # Windows
        # "Microsoft Zira Desktop",   # Windows
    ]
    
    # Try to find the best available voice
    for preferred in preferred_voices:
        for voice in voices:
            if preferred.lower() in voice.name.lower():
                engine.setProperty('voice', voice.id)
                print(f"Using voice: {voice.name}")
                return engine
    
    # Fallback to first available voice
    if voices:
        engine.setProperty('voice', voices[0].id)
        print(f"Using fallback voice: {voices[0].name}")
    
    return engine

engine = init_tts_engine()

def speak(text):
    """Converts text to speech using pyttsx3."""
    print(f"Agent says: {text}")
    engine.say(text)
    engine.runAndWait()

# =========================
# Speech Recognition: Initialize recognizer once
# =========================
recognizer = sr.Recognizer()

def listen_to_command():
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source, duration=0.2)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            command = recognizer.recognize_google(audio)
            print(f"You said: {command}")
            return command.lower()
        except sr.WaitTimeoutError:
            print("No speech detected within timeout.")
            return None
        except sr.UnknownValueError:
            print("Sorry, I didn't understand that.")
            return None
        except sr.RequestError:
            print("API unavailable. Check your internet connection.")
            return None

# =========================
# Memory System
# =========================
def load_memory():
    """Load user memory from file"""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"history": [], "preferences": {}}
    return {"history": [], "preferences": {}}

def save_memory(memory):
    """Save user memory to file"""
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2)

def add_to_history(command, response):
    """Add interaction to history"""
    memory = load_memory()
    timestamp = datetime.datetime.now().isoformat()
    memory["history"].append({
        "timestamp": timestamp,
        "command": command,
        "response": response
    })
    # Keep only the last 100 interactions
    if len(memory["history"]) > 100:
        memory["history"] = memory["history"][-100:]
    save_memory(memory)

# =========================
# Configuration System
# =========================
def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"city": "London", "units": "metric"}  # Default configuration
    return {"city": "London", "units": "metric"}

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# =========================
# Battery helper
# =========================
def get_battery_status():
    battery = psutil.sensors_battery()
    if battery:
        return battery.percent, battery.power_plugged
    return None, None

def describe_battery_health(percentage, is_charging):
    if percentage is None:
        return "Sorry, I can't feel my energy right now."
    if is_charging:
        if percentage >= 95:
            return f"My energy is almost full at {percentage}%. I feel strong and ready for anything!"
        elif percentage >= 70:
            return f"I'm charging and feeling refreshed, already at {percentage}%."
        elif percentage >= 40:
            return f"I'm recharging my strength... currently at {percentage}%. I'll be back to full power soon!"
        else:
            return f"I'm quite drained at {percentage}%, but charging is giving me new life."
    else:
        if percentage >= 80:
            return f"I'm feeling energetic with {percentage}% battery left. Let's keep going!"
        elif percentage >= 50:
            return f"I'm doing fine with {percentage}% battery, but a little top-up later would be nice."
        elif percentage >= 20:
            return f"I'm starting to feel a bit tired... only {percentage}% left."
        else:
            return f"I'm running low at {percentage}% — I really need a charge soon."

# =========================
# Timer helper
# =========================
def set_timer(minutes):
    def timer_callback():
        speak(f"Timer for {minutes} minute{'s' if minutes != 1 else ''} is up!")
    threading.Timer(minutes * 60, timer_callback).start()
    speak(f"Timer set for {minutes} minute{'s' if minutes != 1 else ''}.")

# =========================
# Note-taking helper
# =========================
def take_note(text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(NOTES_FILE, "a") as f:
        f.write(f"[{timestamp}] {text}\n")
    speak(f"Note saved: {text}")

# =========================
# Calendar helper
# =========================
def show_calendar(year=None, month=None):
    """Display calendar for a specific month and year"""
    now = datetime.datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    
    cal = monthcalendar(year, month)
    month_name_str = month_name[month]
    
    # Format calendar display
    result = f"Calendar for {month_name_str} {year}:\n"
    result += "Mo Tu We Th Fr Sa Su\n"
    
    for week in cal:
        week_str = ""
        for day in week:
            if day == 0:
                week_str += "   "
            else:
                week_str += f"{day:2d} "
        result += week_str + "\n"
    
    return result

def parse_date_from_command(command):
    """Extract date information from command"""
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    
    # Simple parsing for month names
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    
    for month_name, month_num in months.items():
        if month_name in command:
            month = month_num
            break
    
    # Look for year numbers
    words = command.split()
    for word in words:
        if word.isdigit() and len(word) == 4 and 2000 <= int(word) <= 2100:
            year = int(word)
    
    return year, month

# =========================
# Weather helper (using free Open-Meteo API)
# =========================
def get_weather(city=None):
    """Get weather information for a city"""
    config = load_config()
    if not city:
        city = config.get("city", "London")
    
    # First, get coordinates for the city using geocoding
    try:
        # Use a free geocoding API
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo_response = requests.get(geo_url)
        geo_data = geo_response.json()
        
        if not geo_data.get("results"):
            return f"Sorry, I couldn't find the city '{city}'."
        
        result = geo_data["results"][0]
        lat = result["latitude"]
        lon = result["longitude"]
        city_name = result["name"]
        
        # Get weather data
        units = config.get("units", "metric")
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "temperature_unit": "celsius" if units == "metric" else "fahrenheit",
            "wind_speed_unit": "kmh" if units == "metric" else "mph",
            "timezone": "auto"
        }
        
        response = requests.get(WEATHER_BASE_URL, params=params)
        data = response.json()
        
        if "current" not in data:
            return f"Sorry, I couldn't get weather for {city_name}."
        
        current = data["current"]
        temp = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        apparent_temp = current["apparent_temperature"]
        wind_speed = current["wind_speed_10m"]
        weather_code = current["weather_code"]
        
        # Map weather codes to descriptions
        weather_descriptions = {
            0: "clear sky",
            1: "mainly clear", 2: "partly cloudy", 3: "overcast",
            45: "fog", 48: "depositing rime fog",
            51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
            61: "slight rain", 63: "moderate rain", 65: "heavy rain",
            80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
            95: "thunderstorm"
        }
        
        description = weather_descriptions.get(weather_code, "unknown weather conditions")
        
        unit_symbol = "°C" if units == "metric" else "°F"
        wind_unit = "km/h" if units == "metric" else "mph"
        
        return (f"Weather in {city_name}: {description}, temperature {temp}{unit_symbol} "
                f"(feels like {apparent_temp}{unit_symbol}), humidity {humidity}%, "
                f"wind speed {wind_speed} {wind_unit}")
    
    except Exception as e:
        return f"Sorry, I couldn't get weather information. Error: {str(e)}"

# =========================
# Calculator helper
# =========================
def calculate_expression(expression):
    """Evaluate a mathematical expression"""
    try:
        # Basic safety check
        allowed_chars = "0123456789+-*/(). "
        if not all(c in allowed_chars for c in expression):
            return "Invalid characters in expression"
        
        # Evaluate the expression
        result = eval(expression)
        return f"The result is {result}"
    except Exception as e:
        return f"Sorry, I couldn't calculate that. Error: {str(e)}"

# =========================
# Disk utilization helper
# =========================
def get_disk_usage(path="/"):
    """Get disk usage information"""
    try:
        usage = shutil.disk_usage(path)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        percent_used = (used_gb / total_gb) * 100
        
        return (f"Disk usage for {path}: {percent_used:.1f}% used, "
                f"{free_gb:.1f} GB free out of {total_gb:.1f} GB total")
    except Exception as e:
        return f"Sorry, I couldn't get disk usage. Error: {str(e)}"

# =========================
# File search and management helper
# =========================
def find_files(pattern, search_path="~"):
    """Find files matching a pattern"""
    try:
        expanded_path = os.path.expanduser(search_path)
        matches = glob.glob(os.path.join(expanded_path, "**", pattern), recursive=True)
        
        if not matches:
            return f"No files found matching '{pattern}' in {search_path}"
        
        if len(matches) > 10:
            return (f"Found {len(matches)} files. Here are the first 10: " + 
                   ", ".join([os.path.basename(m) for m in matches[:10]]))
        else:
            return f"Found {len(matches)} files: " + ", ".join([os.path.basename(m) for m in matches])
    
    except Exception as e:
        return f"Sorry, I couldn't search for files. Error: {str(e)}"

def fuzzy_match_filename(target_name, search_path="~"):
    """Fuzzy match a filename in the search path using difflib."""
    expanded_path = os.path.expanduser(search_path)
    all_files = []
    for root, _, files in os.walk(expanded_path):
        for file in files:
            all_files.append(os.path.join(root, file))
    
    # Normalize target (e.g., "pan card" -> ["pan_card", "pan-card", "pancard"])
    variations = [
        target_name.replace(" ", "_"),
        target_name.replace(" ", "-"),
        target_name.replace(" ", "")
    ]
    
    best_match = None
    best_ratio = 0
    for file_path in all_files:
        file_base = os.path.basename(file_path).lower()
        for var in variations:
            ratio = difflib.SequenceMatcher(None, file_base, var.lower()).ratio()
            if ratio > best_ratio and ratio > 0.7:  # Threshold for good match
                best_ratio = ratio
                best_match = file_path
    
    return best_match

def open_file(file_path, is_image_command=False):
    """Open a file with the default application, or image in Preview. Supports fuzzy matching."""
    try:
        # If no full path, assume it's a name and fuzzy search in common dirs
        if not os.path.isabs(file_path) and not file_path.startswith('~'):
            search_dirs = ["~/Pictures", "~/Documents", "~/Desktop", "~"]
            for dir_path in search_dirs:
                matched_path = fuzzy_match_filename(file_path, dir_path)
                if matched_path:
                    file_path = matched_path
                    break
        
        expanded_path = os.path.expanduser(file_path)
        if not os.path.exists(expanded_path):
            return f"File not found: {file_path}"
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        is_image = is_image_command or any(expanded_path.lower().endswith(ext) for ext in image_extensions)
        
        os_name = platform.system()
        if os_name == "Darwin":
            if is_image:
                process = subprocess.Popen(["open", "-a", "Preview", expanded_path])
            else:
                process = subprocess.Popen(["open", expanded_path])
        elif os_name == "Windows":
            process = subprocess.Popen(["start", expanded_path], shell=True)
        else:  # Linux fallback
            process = subprocess.Popen(["xdg-open", expanded_path], shell=True)
        
        opened_apps[expanded_path] = process
        file_type = "image" if is_image else "file"
        return f"Opened {file_type}: {os.path.basename(expanded_path)}"
    except Exception as e:
        return f"Sorry, I couldn't open the file. Error: {str(e)}"

def close_file(file_path):
    """Close an opened file"""
    try:
        expanded_path = os.path.expanduser(file_path)
        if expanded_path in opened_apps:
            opened_apps[expanded_path].terminate()
            del opened_apps[expanded_path]
            return f"Closed {os.path.basename(expanded_path)}"
        else:
            return f"No open file found with path: {file_path}"
    
    except Exception as e:
        return f"Sorry, I couldn't close the file. Error: {str(e)}"

def get_frontmost_app():
    """Get the name of the frontmost application on macOS."""
    if platform.system() == "Darwin":
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        '''
        try:
            result = subprocess.check_output(["osascript", "-e", script]).decode().strip()
            return result
        except:
            return None
    return None

def close_current_window():
    """Close the currently active window or app on macOS."""
    try:
        os_name = platform.system()
        if os_name == "Darwin":
            front_app = get_frontmost_app()
            if front_app:
                # First try to close window (Cmd+W)
                script = '''
                tell application "System Events"
                    keystroke "w" using command down
                end tell
                '''
                subprocess.run(["osascript", "-e", script], check=True)
                # If that didn't work (e.g., no window), quit the app
                time.sleep(0.5)  # Brief delay to check
                if get_frontmost_app() == front_app:  # Still open?
                    subprocess.run(["osascript", "-e", f'tell application "{front_app}" to quit'], check=True)
                return f"Closed the current window or app ({front_app})."
            else:
                return "No active app found."
        elif os_name == "Windows":
            import pyautogui
            pyautogui.hotkey('alt', 'f4')
            return "Closed the current window."
        else:
            return "Command not supported on this OS."
    except Exception as e:
        return f"Sorry, I couldn't close the window. Error: {str(e)}"

def is_app_running(app_name):
    """Check if an application is running using psutil."""
    app_name_lower = app_name.lower()
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            proc_name = proc.info['name'].lower()
            if app_name_lower in proc_name or proc_name == app_name_lower:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def close_app(app_name):
    """Close a specific application by name."""
    os_name = platform.system()
    try:
        if os_name == "Darwin":
            # Use osascript to quit by exact name
            subprocess.run(["osascript", "-e", f'tell application "{app_name}" to quit'], check=True)
            return f"Closed {app_name}."
        elif os_name == "Windows":
            # Use taskkill
            os.system(f"taskkill /IM {app_name}.exe /F")
            return f"Closed {app_name}."
        else:
            # Linux fallback with pkill
            os.system(f"pkill -f {app_name}")
            return f"Closed {app_name}."
    except Exception as e:
        return f"Sorry, couldn't close {app_name}. Error: {str(e)}"

def list_running_apps():
    """List running user-facing apps."""
    apps = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] and not proc.info['name'].startswith('_'):  # Filter system processes
                apps.append(proc.info['name'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    unique_apps = set(apps[:10])  # Limit to top 10 unique
    if unique_apps:
        response = f"Running apps: {', '.join(unique_apps)}."
    else:
        response = "No running apps detected."
    return response

# =========================
# Network helper
# =========================
def get_network_info():
    """Get network information"""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        return f"Hostname: {hostname}, IP Address: {ip_address}"
    except Exception as e:
        return f"Sorry, I couldn't get network information. Error: {str(e)}"

# =========================
# Help / discoverability
# =========================
def list_available_commands():
    return [
        "logout", "shutdown", "restart",
        "open calculator", "close calculator",
        "open textedit / notepad", "close textedit / notepad",
        "open safari / open browser", "close safari / close browser",
        "close all applications", "empty trash",
        "sleep computer", "lock screen",
        "show desktop", "hide applications",
        "play music", "stop music",
        "hello agent", "are you ready",
        "how are you doing / okay baby / baby / wake up / how is your battery",
        "help",
        "what time is it", "what is today's date",
        "tell me a joke",
        "open youtube", "open google",
        "open downloads", "open documents", "open desktop",
        "open chrome", "close chrome",
        "open firefox", "close firefox",
        "increase volume", "decrease volume", "mute volume", "unmute volume",
        "translate <text> to hindi",
        "set timer for <number> minutes",
        "search for <query>",
        "take a note <text>",
        "show calendar [for <month> [<year>]]",
        "what's the weather [in <city>]",
        "calculate <expression>",
        "disk usage [for <path>]",
        "find files <pattern> [in <path>]",
        "open file <path>",
        "open image <name>",
        "close file <path>",
        "close current window",
        "close current app",
        "close <app_name> (e.g., close finder, close sublime text)",
        "list running apps",
        "what's running",
        "network info",
        "set city to <city>",
        "set units to metric/imperial",
        "what did I ask last time",
    ]

# =========================
# Interpret commands: Use dictionary for faster lookup
# =========================
command_mapping = {
    "logout": "logout",
    "shutdown": "shutdown",
    "restart": "restart",
    "open calculator": "open_calculator",
    "close calculator": "close_calculator",
    "open textedit": "open_textedit",
    "open notepad": "open_textedit",
    "close textedit": "close_textedit",
    "close notepad": "close_textedit",
    "open safari": "open_safari",
    "open browser": "open_safari",
    "close safari": "close_safari",
    "close browser": "close_safari",
    "close all applications": "close_all",
    "empty trash": "empty_trash",
    "sleep computer": "sleep_computer",
    "put computer to sleep": "sleep_computer",
    "lock screen": "lock_screen",
    "lock computer": "lock_screen",
    "show desktop": "show_desktop",
    "hide applications": "hide_applications",
    "play music": "play_music",
    "stop music": "stop_music",
    "hello agent": "greet",
    "are you ready": "greet",
    "how are you doing": "check_battery_status",
    "wake up": "check_battery_status",
    "okay baby": "check_battery_status",
    "baby": "check_battery_status",
    "how is your battery": "check_battery_status",
    "help": "help",
    "what time is it": "tell_time",
    "what's the time": "tell_time",
    "whats the time": "tell_time",
    "today": "tell_date",
    "tell me a joke": "tell_joke",
    "joke": "tell_joke",
    "open youtube": "open_youtube",
    "open google": "open_google",
    "open downloads": "open_downloads",
    "open documents": "open_documents",
    "open desktop": "open_desktop",
    "open chrome": "open_chrome",
    "close chrome": "close_chrome",
    "open firefox": "open_firefox",
    "close firefox": "close_firefox",
    "increase volume": "increase_volume",
    "decrease volume": "decrease_volume",
    "mute volume": "mute_volume",
    "unmute volume": "unmute_volume",
    "translate": "translate_to_hindi",
    "set timer for": "set_timer",
    "search for": "search_web",
    "take a note": "take_note",
    "show calendar": "show_calendar",
    "weather": "get_weather",
    "calculate": "calculate",
    "disk usage": "disk_usage",
    "find files": "find_files",
    "open file": "open_file",
    "open image": "open_image",
    "close file": "close_file",
    "close current window": "close_window",
    "close current app": "close_current_app",
    "close ": "close_app",  # General close app trigger
    "list running apps": "list_running_apps",
    "what's running": "list_running_apps",
    "network info": "network_info",
    "set city to": "set_city",
    "set units to": "set_units",
    "what did i ask": "last_command",
}

def interpret_command(command):
    if not command:
        return None
    for key, action in command_mapping.items():
        if key in command:
            if key == "today" and "date" not in command:
                continue
            return action, command
    return None, None

# =========================
# Execute commands
# =========================
def execute_command(action, command):
    os_name = platform.system()
    response = "Command executed."

    if action == "greet":
        response = "Yeah, go ahead and ask questions. I can help with things like opening apps, playing music, translating to Hindi, setting timers, and more!"
        speak(response)

    elif action == "check_battery_status":
        battery_percentage, is_charging = get_battery_status()
        response = describe_battery_health(battery_percentage, is_charging)
        speak(response)

    elif action == "logout":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "System Events" to log out'], check=True)
            response = "Logging out."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "shutdown":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "Finder" to shut down'], check=True)
            response = "Shutting down."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "restart":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "Finder" to restart'], check=True)
            response = "Restarting."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_calculator":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
            response = "Opening Calculator."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_calculator":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Calculator" to quit'], check=True)
            response = "Calculator closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_textedit":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "TextEdit"])
            response = "Opening TextEdit."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_textedit":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "TextEdit" to quit'], check=True)
            response = "TextEdit closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_safari":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Safari", "https://www.google.com"])
            response = "Opening Safari."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_safari":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Safari" to quit'], check=True)
            response = "Safari closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_all":
        if os_name == "Darwin":
            script = '''
            tell application "System Events"
                set app_list to name of every process whose background only is false
                repeat with app_name in app_list
                    if app_name is not "Finder" then
                        tell application app_name to quit
                    end if
                end repeat
            end tell
            '''
            subprocess.run(["osascript", "-e", script], check=True)
            response = "All applications closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "empty_trash":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'], check=True)
            response = "Trash emptied."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "sleep_computer":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], check=True)
            response = "Putting computer to sleep."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "lock_screen":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'], check=True)
            response = "Locking screen."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "show_desktop":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to activate'], check=True)
            subprocess.run(["osascript", "-e", 'tell application "Finder" to set collapsed of every window to true'], check=True)
            response = "Showing desktop."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "hide_applications":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of every process to false'], check=True)
            response = "Hiding applications."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "play_music":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Music" to play'], check=True)
            response = "Playing music."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "stop_music":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Music" to pause'], check=True)
            response = "Music stopped."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "help":
        commands = list_available_commands()
        response = "Here are some things you can ask me to do: " + ", ".join(commands[:5]) + " and more."
        speak(response)
        for cmd in commands:
            print(f"- {cmd}")

    elif action == "tell_time":
        response = f"The time is {datetime.datetime.now().strftime('%I:%M %p')}"
        speak(response)

    elif action == "tell_date":
        response = f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}"
        speak(response)

    elif action == "tell_joke":
        jokes = [
            "Why don't skeletons fight each other? They don't have the guts.",
            "I told my computer I needed a break, and it said no problem, it'll go to sleep.",
            "Why was the math book sad? It had too many problems.",
            "I would tell you a UDP joke, but you might not get it."
        ]
        response = random.choice(jokes)
        speak(response)

    elif action == "open_youtube":
        webbrowser.open("https://www.youtube.com")
        response = "Opening YouTube."
        speak(response)

    elif action == "open_google":
        webbrowser.open("https://www.google.com")
        response = "Opening Google."
        speak(response)

    elif action == "open_downloads":
        path = os.path.expanduser("~/Downloads")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            response = "Opening Downloads folder."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_documents":
        path = os.path.expanduser("~/Documents")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            response = "Opening Documents folder."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_desktop":
        path = os.path.expanduser("~/Desktop")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            response = "Opening Desktop."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_chrome":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Google Chrome"])
            response = "Opening Chrome."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_chrome":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'], check=True)
            response = "Chrome closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "open_firefox":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Firefox"])
            response = "Opening Firefox."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "close_firefox":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Firefox" to quit'], check=True)
            response = "Firefox closed."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "increase_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set o to (output volume of (get volume settings))' -e 'set volume output volume (o + 10)'")
            response = "Volume increased."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "decrease_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set o to (output volume of (get volume settings))' -e 'set volume output volume (o - 10)'")
            response = "Volume decreased."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "mute_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set volume output muted true'")
            response = "Volume muted."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "unmute_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set volume output muted false'")
            response = "Volume unmuted."
            speak(response)
        else:
            response = "Command not applicable to this OS."
            print(response)

    elif action == "translate_to_hindi":
        if "translate" in command and "to hindi" in command:
            text_to_translate = command.split("translate")[1].split("to hindi")[0].strip()
            if text_to_translate:
                try:
                    translator = GoogleTranslator(source='en', target='hi')
                    translated_text = translator.translate(text_to_translate)
                    response = f"The translation of '{text_to_translate}' to Hindi is: {translated_text}"
                    speak(response)
                    print(f"Translation: {translated_text}")
                except Exception as e:
                    response = "Sorry, I couldn't translate that. Please check your internet connection."
                    speak(response)
                    print(f"Translation error: {e}")
            else:
                response = "Please provide text to translate to Hindi."
                speak(response)
        else:
            response = "Please say 'translate <text> to Hindi' to use the translation feature."
            speak(response)

    elif action == "set_timer":
        try:
            minutes_str = command.split("set timer for")[1].split("minute")[0].strip()
            minutes = float(minutes_str)
            if minutes > 0:
                set_timer(minutes)
                response = f"Timer set for {minutes} minute{'s' if minutes != 1 else ''}."
            else:
                response = "Please specify a positive number of minutes for the timer."
                speak(response)
        except (ValueError, IndexError):
            response = "Please say 'set timer for <number> minutes' to set a timer."
            speak(response)

    elif action == "search_web":
        query = command.split("search for")[1].strip() if "search for" in command else ""
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            response = f"Searching for {query}."
            speak(response)
        else:
            response = "Please provide a search query."
            speak(response)

    elif action == "take_note":
        note_text = command.split("take a note")[1].strip() if "take a note" in command else ""
        if note_text:
            take_note(note_text)
            response = f"Note saved: {note_text}"
        else:
            response = "Please provide text for the note."
            speak(response)

    # New commands
    elif action == "show_calendar":
        year, month = parse_date_from_command(command)
        calendar_text = show_calendar(year, month)
        print(calendar_text)
        response = f"Showing calendar for {month_name[month]} {year}"
        speak(response)

    elif action == "get_weather":
        if "weather in" in command:
            city = command.split("weather in")[1].strip()
        else:
            city = None
        response = get_weather(city)
        speak(response)

    elif action == "calculate":
        if "calculate" in command:
            expression = command.split("calculate")[1].strip()
            response = calculate_expression(expression)
            speak(response)
        else:
            response = "Please provide an expression to calculate."
            speak(response)

    elif action == "disk_usage":
        if "disk usage for" in command:
            path = command.split("disk usage for")[1].strip()
        else:
            path = "/"
        response = get_disk_usage(path)
        speak(response)

    elif action == "find_files":
        if "find files" in command:
            parts = command.split("find files")[1].strip().split(" in ")
            pattern = parts[0].strip()
            search_path = parts[1].strip() if len(parts) > 1 else "~"
            response = find_files(pattern, search_path)
            speak(response)
        else:
            response = "Please provide a file pattern to search for."
            speak(response)

    elif action == "open_file":
        if "open file" in command:
            file_path = command.split("open file")[1].strip()
            response = open_file(file_path)
            speak(response)
        else:
            response = "Please specify a file path or name to open."
            speak(response)

    elif action == "open_image":
        if "open image" in command:
            file_name = command.split("open image")[1].strip()
            response = open_file(file_name, is_image_command=True)
            speak(response)
        else:
            response = "Please specify an image name or path."
            speak(response)

    elif action == "close_file":
        if "close file" in command:
            file_path = command.split("close file")[1].strip()
            response = close_file(file_path)
            speak(response)
        else:
            response = "Please specify a file path to close."
            speak(response)

    elif action == "close_window":
        response = close_current_window()
        speak(response)

    elif action == "close_current_app":
        front_app = get_frontmost_app()
        if front_app:
            subprocess.run(["osascript", "-e", f'tell application "{front_app}" to quit'], check=True)
            response = f"Closed {front_app}."
        else:
            response = "No active app to close."
        speak(response)

    elif action == "close_app":
        if "close " in command:
            app_name = command.split("close ")[1].strip()
            if is_app_running(app_name):
                response = close_app(app_name)
            else:
                response = f"{app_name} is not running."
            speak(response)
        else:
            response = "Please specify an app name to close, like 'close finder'."
            speak(response)

    elif action == "list_running_apps":
        response = list_running_apps()
        speak(response)
        print(response)

    elif action == "network_info":
        response = get_network_info()
        speak(response)

    elif action == "set_city":
        if "set city to" in command:
            city = command.split("set city to")[1].strip()
            config = load_config()
            config["city"] = city
            save_config(config)
            response = f"City set to {city}."
            speak(response)
        else:
            response = "Please specify a city name."
            speak(response)

    elif action == "set_units":
        if "set units to" in command:
            units = command.split("set units to")[1].strip()
            if units in ["metric", "imperial"]:
                config = load_config()
                config["units"] = units
                save_config(config)
                response = f"Units set to {units}."
                speak(response)
            else:
                response = "Please specify either 'metric' or 'imperial'."
                speak(response)
        else:
            response = "Please specify units."
            speak(response)

    elif action == "last_command":
        memory = load_memory()
        if memory["history"]:
            last = memory["history"][-1]
            response = f"Last time you asked: '{last['command']}' and I responded: '{last['response']}'"
            speak(response)
        else:
            response = "I don't have any history of our conversation yet."
            speak(response)

    else:
        response = "Command not recognized or supported on this operating system."
        print(response)

    # Add to memory
    add_to_history(command, response)

# =========================
# Main loop
# =========================
if __name__ == "__main__":
    # Initialize memory and config files if they don't exist
    load_memory()
    load_config()
    
    speak("Voice agent initialized and ready!")
    
    while True:
        try:
            command = listen_to_command()
            if command:
                action, full_command = interpret_command(command)
                if action:
                    execute_command(action, full_command)
                else:
                    commands = list_available_commands()
                    response = "Hey, hey baby — try different words. I can help with things like: " + ", ".join(commands[:5])
                    # speak(response)
                    for cmd in commands:
                        print(f"- {cmd}")
            time.sleep(0.1)  # Prevent excessive CPU usage
        except KeyboardInterrupt:
            speak("Shutting down the agent. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            speak("Oops, something went wrong. Try again!")