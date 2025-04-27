import litserve as ls
import whisper

class WhisperLitAPI(ls.LitAPI):
    def setup(self, device):
        # Load the OpenAI Whisper model. You can specify other models like "base", "small", etc.
        self.model = whisper.load_model("large", device='cuda')
    
    def decode_request(self, request):
        # Assuming the request sends the path to the audio file
        # In a more robust implementation, you would handle audio data directly.
        return request["audio_path"]
    
    def predict(self, audio_path):
        # Process the audio file and return the transcription result
        result = self.model.transcribe(audio_path)
        return result
    
    def encode_response(self, output):
        # Return the transcription text
        return {"transcription": output["text"]}

if __name__ == "__main__":
    api = WhisperLitAPI()
    server = ls.LitServer(api, accelerator="gpu", timeout=1000, workers_per_device=2)
    server.run(port=5070)