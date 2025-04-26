import io, base64, torch
import numpy as np
import soundfile as sf
import litserve as ls
from TTS.api import TTS

SPEAKER_WAV_FILE = "/teamspace/studios/this_studio/speakers/obama.wav"
LANGUAGE = "en"

class TTSTextToWavLitAPI(ls.LitAPI):
    def setup(self, device):
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        print('setup complete...')

    def decode_request(self, request):
        return request["text"]

    def predict(self, text):
        wav = self.tts.tts(text=text, speaker_wav=SPEAKER_WAV_FILE, language=LANGUAGE)
        if isinstance(wav, torch.Tensor):
            wav = wav.numpy()

        # Write the numpy array to an in-memory buffer in WAV format
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, wav, samplerate=22050, format='WAV')
        audio_buffer.seek(0)
        audio_data = audio_buffer.getvalue()
        audio_buffer.close()

        return {"audio_content": audio_data}

    def encode_response(self, prediction):
        audio_content_base64 = base64.b64encode(prediction["audio_content"]).decode("utf-8")
        return {"audio_content": audio_content_base64, "content_type": "audio/wav"}

if __name__ == "__main__":
    api = TTSTextToWavLitAPI()
    server = ls.LitServer(api)
    server.run(port=5070)