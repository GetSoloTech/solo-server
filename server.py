import litserve as ls
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class SoloServerAPI(ls.LitAPI):
    """
    A standardized LitServe API for model import and inference.
    This Solo Server loads a transformer model (e.g., GPT-2) and exposes
    a prediction endpoint.
    """

    def setup(self, device):
        # Choose device: use GPU if available, otherwise CPU.
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load the model and tokenizer (using GPT-2 as an example).
        self.tokenizer = AutoTokenizer.from_pretrained("gpt2")
        self.model = AutoModelForCausalLM.from_pretrained("gpt2").to(self.device)
    
    def decode_request(self, request):
        """
        Extract the 'prompt' field from the incoming JSON request.
        """
        return request.get("prompt", "")
    
    def predict(self, prompt):
        """
        Perform inference: tokenize the prompt, generate output tokens,
        and decode the generated sequence.
        """
        # Tokenize input text.
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        # Generate output tokens (limiting to 50 new tokens).
        outputs = self.model.generate(**inputs, max_new_tokens=50)
        # Decode and return the generated text.
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    def encode_response(self, response):
        """
        Format the prediction output as a JSON-serializable response.
        """
        return {"generated_text": response}

if __name__ == "__main__":
    # Initialize the Solo Server API.
    api = SoloServerAPI()
    # Create a LitServe server instance with auto device detection.
    server = ls.LitServer(api, accelerator="auto", max_batch_size=1)
    # Run the server on port 8000.
    server.run(port=8000)
