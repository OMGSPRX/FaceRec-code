import pyttsx3
from queue import Queue

# Fungsi untuk menginisialisasi text-to-speech engine
def initialize_text_to_speech_engine():
    engine = pyttsx3.init()
    return engine

# Fungsi untuk menjalankan text-to-speech engine di thread terpisah
def speak_from_queue(queue, engine):
    while True:
        text = queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
