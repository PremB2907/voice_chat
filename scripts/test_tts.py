from TTS.api import TTS

tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)
tts.tts_to_file(text="Hello Prem. Your voice chat system is now alive.", file_path="output.wav")
