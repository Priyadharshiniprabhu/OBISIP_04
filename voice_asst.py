import speech_recognition as sr
import pyttsx3
import requests
import threading
from transformers import pipeline
from google.oauth2.credentials import Credentials
import pytz
from datetime import datetime, timedelta
import base64
from googleapiclient.discovery import build
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import wikipedia
import os
import tensorflow as tf
import spacy

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

nlp_spacy = spacy.load('en_core_web_sm')
nlp_transformers = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

engine = pyttsx3.init()

def speak(text):
    print(f"[SPEAKING]: {text}") 
    threading.Thread(target=lambda: engine.say(text)).start()
    engine.runAndWait()

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)

        try:
            text = recognizer.recognize_google(audio)
            print(f"[RECOGNIZED]: {text}") 
            return text.lower()
        except sr.UnknownValueError:
            speak("Sorry, I did not understand that.")
            return None
        except sr.RequestError:
            speak("Sorry, I'm having trouble accessing the microphone.")
            return None

def process_intent_transformers(command):
    candidate_labels = [
        'get_weather', 'send_email', 'set_reminder', 
        'play_music', 'general_knowledge', 'greeting'
    ]
    result = nlp_transformers(command, candidate_labels)
    intent = result['labels'][0]
    print(f"[INTENT]: {intent}")  
    return intent

def get_weather(city):
    api_key = '70bcf74ca6138e62bfcfe00ce7d6e89e' 
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        output = f"The weather in {city} is {weather} with a temperature of {temp} degrees Celsius."
        print(output) 
        speak(output)
    else:
        speak("Sorry, I couldn't fetch the weather.")

def send_email(subject, body, to):
    try:
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        creds = Credentials.from_authorized_user_file('token.json', SCOPES) 
        service = build('gmail', 'v1', credentials=creds)

        message = create_message('priyadharshini.p246736@gmail.com', to, subject, body)
        send_message(service, 'me', message)
        output = "Email sent successfully!"
        print(output) 
        speak(output)
    except Exception as e:
        output = f"Failed to send email. Error: {e}"
        print(output) 
        speak(output)

def create_message(sender, to, subject, body):
    message = f"To: {to}\nSubject: {subject}\n\n{body}"
    return {'raw': base64.urlsafe_b64encode(message.encode()).decode()}

def send_message(service, user_id, message):
    service.users().messages().send(userId=user_id, body=message).execute()

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="dab0a5bcf28f42d1b504cba6c22603bd",
    client_secret="d72c9e3f360846368355152888b505b5",
    redirect_uri="http://localhost:8888/callback",
    scope="user-modify-playback-state user-read-playback-state"
))

def play_song():
    speak("Which song would you like to hear?")
    song_name = recognize_speech()
    if song_name:
        results = sp.search(q=song_name, type='track', limit=1)
        if results['tracks']['items']:
            track = results['tracks']['items'][0]
            song_title = track['name']
            artist = track['artists'][0]['name']
            output = f"I found {song_title} by {artist}. Unfortunately, I can't play it because a Premium account is required."
            print(output)
            speak(output)
        else:
            speak("Sorry, I couldn't find that song.")
    else:
        speak("Sorry, I couldn't understand the song name.")

def convert_to_ist(dt):
    ist = pytz.timezone('Asia/Kolkata')
    return ist.localize(dt).isoformat()

def set_reminder(summary, minutes_from_now):
    start_time = datetime.now() + timedelta(minutes=minutes_from_now)
    end_time = start_time + timedelta(minutes=5)  

    start_time_str = convert_to_ist(start_time)
    end_time_str = convert_to_ist(end_time)

    create_calendar_event(summary, start_time_str, end_time_str)

def load_credentials():
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        raise FileNotFoundError("The 'token.json' file was not found. Please ensure it exists in the working directory.")
    return creds

def create_calendar_event(summary, start_time, end_time):
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'},
    }

    service.events().insert(calendarId='primary', body=event).execute()
    output = "Reminder set successfully."
    print(output)  
    speak(output)

def get_general_knowledge(query):
    try:
        summary = wikipedia.summary(query, sentences=2)
        print(f"[WIKIPEDIA SUMMARY]: {summary}")  
        speak(summary)
    except wikipedia.exceptions.DisambiguationError:
        speak("That query is ambiguous. Please be more specific.")
    except wikipedia.exceptions.PageError:
        speak("Sorry, I couldn't find any information on that topic.")
    except Exception as e:
        speak(f"An error occurred: {str(e)}")

def handle_command(command):
    intent = process_intent_transformers(command)

    if intent == 'greeting':
        speak("I'm fine, thank you! How can I assist you today?")
    elif intent == 'get_weather':
        speak("Which city?")
        city = recognize_speech()
        if city:
            get_weather(city)
    elif intent == 'send_email':
        speak("What is the subject?")
        subject = recognize_speech()
        speak("What is the body?")
        body = recognize_speech()
        speak("Who do you want to send it to?")
        to = recognize_speech()
        if subject and body and to:
            send_email(subject, body, to)
    elif intent == 'play_music':
        play_song()
    elif intent == 'set_reminder':
        speak("What is the reminder?")
        summary = recognize_speech()
        speak("In how many minutes?")
        minutes = recognize_speech()
        if minutes and minutes.isdigit():
            set_reminder(summary, int(minutes))
        else:
            speak("Please provide a valid number for minutes.")
    elif intent == 'general_knowledge':
        speak("What would you like to know?")
        query = recognize_speech()
        if query:
            get_general_knowledge(query)
    else:
        speak("Sorry, I didn't understand that.")

def main():
    print("How can I assist you today?")
    while True:
        command = recognize_speech()
        if command is None:
            print("No command detected. Please try again.")
            continue
        if "exit" in command:
            print("Goodbye!")
            speak("Goodbye!")
            break
        handle_command(command)

if __name__ == "__main__":
    main()
