import litserve as ls
import torch
from io import BytesIO
from PIL import Image
from transformers import AutoModel, AutoTokenizer

class MiniCPMAPI(ls.LitAPI):
    def setup(self, device):
        # Load the model
        self.model = AutoModel.from_pretrained('openbmb/MiniCPM-V-2_6', trust_remote_code=True,
            attn_implementation='sdpa', torch_dtype=torch.bfloat16) # sdpa or flash_attention_2, no eager
        self.model = self.model.eval().cuda()
        self.tokenizer = AutoTokenizer.from_pretrained('openbmb/MiniCPM-V-2_6', trust_remote_code=True)


    def decode_request(self, request):
        # Extract file from request
        return (request["content"].file, request["prompt"])

    def predict(self, input):
        # Pass the image and prompt to the model
        image = Image.open(input[0]).convert('RGB')
        msgs = [{'role': 'user', 'content': [image, input[1]]}]

        res = self.model.chat(
            image=None,
            msgs=msgs,
            tokenizer=self.tokenizer
        )
        return res

    def encode_response(self, result):
        return result

# Starting the server
if __name__ == "__main__":
    api = MiniCPMAPI()
    server = ls.LitServer(api, timeout=False)
    server.run(port=5070)