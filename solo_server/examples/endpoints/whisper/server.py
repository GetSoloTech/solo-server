from model import Llama3
import litserve as ls

class Llama3VisionAPI(ls.LitAPI):
    def setup(self, device):
        self.model = Llama3(device)

    def decode_request(self, request):
        return self.model.apply_chat_template(request.messages)

    def predict(self, inputs, context):
        yield self.model(inputs)

    def encode_response(self, outputs):
        for output in outputs:
            yield {"role": "assistant", "content": self.model.decode_tokens(output)}

if __name__ == "__main__":
    api = Llama3VisionAPI()
    server = ls.LitServer(api, spec=ls.OpenAISpec())
    server.run(port=5070)