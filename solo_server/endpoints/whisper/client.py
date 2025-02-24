import requests
import os
import argparse

def transcribe_audio(audio_file_path):
    url = "http://127.0.0.1:8000/predict"
    response = requests.post(url, json={"audio_path": audio_file_path})
    print(response.json())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio files")
    parser.add_argument("--file", help="Filename of the audio file to transcribe", type=str, default='mlk.mp3')
    args = parser.parse_args()
    
    # call the model with the file
    audio_path = os.path.join(os.getcwd(), 'audio_samples', args.file)
    transcribe_audio(audio_path)