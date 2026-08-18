"""
Audio Transcriber
------------------
Wraps OpenAI's open-source Whisper model to turn call recordings into text.
This is the first stage of the pipeline: audio_path -> transcript -> scorer.py

Model size tradeoff:
  - "tiny"/"base": fast, decent for clear audio, good for local dev/demo
  - "small"/"medium": better accuracy, slower, needs more RAM
  - "large-v3": best accuracy, needs a GPU for reasonable speed

For a portfolio demo, "base" is a good default - runs on CPU in a few seconds
per minute of audio.
"""
import os
from openai import OpenAI

def get_openai_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def transcribe_audio(audio_path: str, language: str = "en") -> dict:
    """
    Transcribe an audio file to text using OpenAI Whisper API.
    Returns {"text": full transcript, "language": detected}
    """
    client = get_openai_client()
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            language=language
        )

    return {
        "text": transcript.text.strip(),
        "language": language,
    }
