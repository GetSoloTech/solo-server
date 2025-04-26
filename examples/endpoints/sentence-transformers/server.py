from sentence_transformers import SentenceTransformer
import litserve as ls

class EmbeddingAPI(ls.LitAPI):
    def setup(self, device):
        self.instruction = "Represent this sentence for searching relevant passages: "
        self.model = SentenceTransformer('BAAI/bge-large-en-v1.5', device=device)

    def decode_request(self, request):
        return request["input"]

    def predict(self, query):
        return self.model.encode([self.instruction + query], normalize_embeddings=True)

    def encode_response(self, output):
        return {"embedding": output[0].tolist()}

if __name__ == "__main__":
    api = EmbeddingAPI()
    server = ls.LitServer(api)
    server.run(port=5070)