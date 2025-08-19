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
from deep_translator import GoogleTranslator

# =========================
# Speech: Initialize engine once, prioritize Samantha
# =========================
engine = pyttsx3.init()
engine.setProperty('rate', 235)  # Keep your preferred rate
engine.setProperty('volume', 1.0)

voices = engine.getProperty('voices')
preferred_names = ["samantha", "ava"]  # Prioritize Samantha, then Ava
picked = False
for v in voices:
    if "samantha" in v.name.lower():
        engine.setProperty('voice', v.id)
        picked = True
        break
if not picked:
    for v in voices:
        if any(name in v.name.lower() for name in preferred_names):
            engine.setProperty('voice', v.id)
            picked = True
            break
if not picked and voices:
    engine.setProperty('voice', voices[0].id)  # Fallback to default

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
    notes_file = os.path.expanduser("~/Documents/agent_notes.txt")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(notes_file, "a") as f:
        f.write(f"[{timestamp}] {text}\n")
    speak(f"Note saved: {text}")

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
        "what time is it", "what is today’s date",
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

    if action == "greet":
        speak("Yeah, go ahead and ask questions. I can help with things like opening apps, playing music, translating to Hindi, setting timers, and more!")

    elif action == "check_battery_status":
        battery_percentage, is_charging = get_battery_status()
        health_message = describe_battery_health(battery_percentage, is_charging)
        speak(health_message)

    elif action == "logout":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "System Events" to log out'], check=True)
            speak("Logging out.")
        else:
            print("Command not applicable to this OS.")

    elif action == "shutdown":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "Finder" to shut down'], check=True)
            speak("Shutting down.")
        else:
            print("Command not applicable to this OS.")

    elif action == "restart":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell app "Finder" to restart'], check=True)
            speak("Restarting.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_calculator":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Calculator"])
            speak("Opening Calculator.")
        else:
            print("Command not applicable to this OS.")

    elif action == "close_calculator":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Calculator" to quit'], check=True)
            speak("Calculator closed.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_textedit":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "TextEdit"])
            speak("Opening TextEdit.")
        else:
            print("Command not applicable to this OS.")

    elif action == "close_textedit":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "TextEdit" to quit'], check=True)
            speak("TextEdit closed.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_safari":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Safari", "https://www.google.com"])
            speak("Opening Safari.")
        else:
            print("Command not applicable to this OS.")

    elif action == "close_safari":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Safari" to quit'], check=True)
            speak("Safari closed.")
        else:
            print("Command not applicable to this OS.")

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
            speak("All applications closed.")
        else:
            print("Command not applicable to this OS.")

    elif action == "empty_trash":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'], check=True)
            speak("Trash emptied.")
        else:
            print("Command not applicable to this OS.")

    elif action == "sleep_computer":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], check=True)
            speak("Putting computer to sleep.")
        else:
            print("Command not applicable to this OS.")

    elif action == "lock_screen":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'], check=True)
            speak("Locking screen.")
        else:
            print("Command not applicable to this OS.")

    elif action == "show_desktop":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to activate'], check=True)
            subprocess.run(["osascript", "-e", 'tell application "Finder" to set collapsed of every window to true'], check=True)
            speak("Showing desktop.")
        else:
            print("Command not applicable to this OS.")

    elif action == "hide_applications":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "System Events" to set visible of every process to false'], check=True)
            speak("Hiding applications.")
        else:
            print("Command not applicable to this OS.")

    elif action == "play_music":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Music" to play'], check=True)
            speak("Playing music.")
        else:
            print("Command not applicable to this OS.")

    elif action == "stop_music":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Music" to pause'], check=True)
            speak("Music stopped.")
        else:
            print("Command not applicable to this OS.")

    elif action == "help":
        commands = list_available_commands()
        speak("Here are some things you can ask me to do: " + ", ".join(commands))
        for cmd in commands:
            print(f"- {cmd}")

    elif action == "tell_time":
        speak(f"The time is {datetime.datetime.now().strftime('%I:%M %p')}")

    elif action == "tell_date":
        speak(f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}")

    elif action == "tell_joke":
        jokes = [
            "Why don’t skeletons fight each other? They don’t have the guts.",
            "I told my computer I needed a break, and it said no problem, it’ll go to sleep.",
            "Why was the math book sad? It had too many problems.",
            "I would tell you a UDP joke, but you might not get it."
        ]
        speak(random.choice(jokes))

    elif action == "open_youtube":
        webbrowser.open("https://www.youtube.com")
        speak("Opening YouTube.")

    elif action == "open_google":
        webbrowser.open("https://www.google.com")
        speak("Opening Google.")

    elif action == "open_downloads":
        path = os.path.expanduser("~/Downloads")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            speak("Opening Downloads folder.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_documents":
        path = os.path.expanduser("~/Documents")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            speak("Opening Documents folder.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_desktop":
        path = os.path.expanduser("~/Desktop")
        if os_name == "Darwin":
            subprocess.Popen(["open", path])
            speak("Opening Desktop.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_chrome":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Google Chrome"])
            speak("Opening Chrome.")
        else:
            print("Command not applicable to this OS.")

    elif action == "close_chrome":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'], check=True)
            speak("Chrome closed.")
        else:
            print("Command not applicable to this OS.")

    elif action == "open_firefox":
        if os_name == "Darwin":
            subprocess.Popen(["open", "-a", "Firefox"])
            speak("Opening Firefox.")
        else:
            print("Command not applicable to this OS.")

    elif action == "close_firefox":
        if os_name == "Darwin":
            subprocess.run(["osascript", "-e", 'tell application "Firefox" to quit'], check=True)
            speak("Firefox closed.")
        else:
            print("Command not applicable to this OS.")

    elif action == "increase_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set o to (output volume of (get volume settings))' -e 'set volume output volume (o + 10)'")
            speak("Volume increased.")
        else:
            print("Command not applicable to this OS.")

    elif action == "decrease_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set o to (output volume of (get volume settings))' -e 'set volume output volume (o - 10)'")
            speak("Volume decreased.")
        else:
            print("Command not applicable to this OS.")

    elif action == "mute_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set volume output muted true'")
            speak("Volume muted.")
        else:
            print("Command not applicable to this OS.")

    elif action == "unmute_volume":
        if os_name == "Darwin":
            os.system("osascript -e 'set volume output muted false'")
            speak("Volume unmuted.")
        else:
            print("Command not applicable to this OS.")

    elif action == "translate_to_hindi":
        if "translate" in command and "to hindi" in command:
            text_to_translate = command.split("translate")[1].split("to hindi")[0].strip()
            if text_to_translate:
                try:
                    translator = GoogleTranslator(source='en', target='hi')
                    translated_text = translator.translate(text_to_translate)
                    speak(f"The translation of '{text_to_translate}' to Hindi is: {translated_text}")
                    print(f"Translation: {translated_text}")
                except Exception as e:
                    speak("Sorry, I couldn't translate that. Please check your internet connection.")
                    print(f"Translation error: {e}")
            else:
                speak("Please provide text to translate to Hindi.")
        else:
            speak("Please say 'translate <text> to Hindi' to use the translation feature.")

    elif action == "set_timer":
        try:
            minutes_str = command.split("set timer for")[1].split("minute")[0].strip()
            minutes = float(minutes_str)
            if minutes > 0:
                set_timer(minutes)
            else:
                speak("Please specify a positive number of minutes for the timer.")
        except (ValueError, IndexError):
            speak("Please say 'set timer for <number> minutes' to set a timer.")

    elif action == "search_web":
        query = command.split("search for")[1].strip() if "search for" in command else ""
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            speak(f"Searching for {query}.")
        else:
            speak("Please provide a search query.")

    elif action == "take_note":
        note_text = command.split("take a note")[1].strip() if "take a note" in command else ""
        if note_text:
            take_note(note_text)
        else:
            speak("Please provide text for the note.")

    else:
        print("Command not recognized or supported on this operating system.")

# =========================
# Main loop
# =========================
if __name__ == "__main__":
    while True:
        try:
            command = listen_to_command()
            if command:
                action, full_command = interpret_command(command)
                if action:
                    execute_command(action, full_command)
                else:
                    commands = list_available_commands()
                    speak("Hey, hey baby — try different words. I can help with things like: " + ", ".join(commands))
                    for cmd in commands:
                        print(f"- {cmd}")
            time.sleep(0.1)  # Prevent excessive CPU usage
        except KeyboardInterrupt:
            speak("Shutting down the agent. Goodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            speak("Oops, something went wrong. Try again!")