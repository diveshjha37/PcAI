import speech_recognition as sr
import webbrowser
import subprocess
import pyttsx3
import os
import psutil  # For process management

# Initialize the recognizer and the text-to-speech engine
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Set the Lekha voice
lekha_voice_id = "com.apple.speech.synthesis.voice.lekha"
voices = engine.getProperty('voices')

# Find and set the Lekha voice
for voice in voices:
    if lekha_voice_id in voice.id:
        engine.setProperty('voice', voice.id)
        print(f"Using voice: {voice.name} ({voice.id})")
        break
else:
    print(f"Voice '{lekha_voice_id}' not found. Using default voice.")

def speak(text):
    """Function to speak the given text."""
    engine.say(text)
    engine.runAndWait()

def take_command():
    """Function to capture voice command from the user."""
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

        try:
            print("Recognizing...")
            command = recognizer.recognize_google(audio, language='en-US')
            print(f"User said: {command}\n")
            return command.lower()
        except sr.UnknownValueError:
            # Do not respond if the input is unclear
            return None
        except sr.RequestError:
            speak("Sorry, my speech service is down.")
            return None

def open_application(command):
    """Function to open applications based on the command."""
    if 'open browser' in command:
        speak("Opening browser")
        webbrowser.open("https://www.google.com")
    elif 'open gmail' in command:
        speak("Opening Gmail but you will need to login because of security reasons")
        webbrowser.open("https://www.gmail.com")
    elif 'open terminal' in command:
        speak("Opening Terminal")
        if os.name == 'nt':  # Windows
            subprocess.Popen(["cmd.exe"])
        else:  # Linux/macOS
            subprocess.Popen(["open", "-a", "Terminal"])  # Open Terminal on macOS
    elif 'open calculator' in command:
        speak("Opening Calculator")
        if os.name == 'nt':  # Windows
            subprocess.Popen("calc.exe")
        else:  # Linux/macOS
            subprocess.Popen(["open", "-a", "Calculator"])  # Open Calculator on macOS
    else:
        # Do not respond if the command is not recognized
        return

def get_running_browsers():
    """Function to get a list of running browsers."""
    browsers = ["Safari", "Google Chrome", "Brave Browser", "Firefox", "Microsoft Edge"]
    running_browsers = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] in browsers:
                running_browsers.append(proc.info['name'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return running_browsers

def close_browser():
    """Function to close one or all browsers based on user input."""
    running_browsers = get_running_browsers()
    if not running_browsers:
        speak("No browsers are currently running.")
        return

    speak("I found the following browsers running: " + ", ".join(running_browsers))
    speak("Which browser would you like to close? You can say 'all' to close all browsers.")
    command = take_command()

    if not command:
        speak("I didn't understand your response.")
        return

    if 'all' in command:
        for browser in running_browsers:
            try:
                subprocess.run(["pkill", "-9", browser], check=True)
                speak(f"{browser} closed forcefully.")
                print(f"{browser} closed forcefully.")
            except subprocess.CalledProcessError:
                speak(f"Could not close {browser}.")
                print(f"Could not close {browser}.")
    else:
        for browser in running_browsers:
            if browser.lower() in command:
                try:
                    subprocess.run(["pkill", "-9", browser], check=True)
                    speak(f"{browser} closed forcefully.")
                    print(f"{browser} closed forcefully.")
                except subprocess.CalledProcessError:
                    speak(f"Could not close {browser}.")
                    print(f"Could not close {browser}.")
                return
        speak("I didn't find any matching browser to close.")

if __name__ == "__main__":
    speak("Hello, how can I assist you today?")
    while True:
        command = take_command()
        if command:
            if 'exit' in command or 'quit' in command:
                speak("Goodbye!")
                break
            elif 'close browser' in command or 'stop browser' in command:
                close_browser()
            else:
                open_application(command)