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
import whisper
import functools

_MODEL_CACHE = {}


@functools.lru_cache(maxsize=None)
def _load_model(model_size: str = "base"):
    return whisper.load_model(model_size)


def transcribe_audio(audio_path: str, model_size: str = "base", language: str = "en") -> dict:
    """
    Transcribe an audio file to text.
    Returns {"text": full transcript, "segments": [...], "language": detected}
    """
    model = _load_model(model_size)
    result = model.transcribe(audio_path, language=language, fp16=False)
    return {
        "text": result["text"].strip(),
        "segments": result.get("segments", []),
        "language": result.get("language", language),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <audio_file_path>")
        sys.exit(1)
    out = transcribe_audio(sys.argv[1])
    print(out["text"])
