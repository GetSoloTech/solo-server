# Import necessary libraries
import torch
import litserve as ls
from gliner import GLiNER


class GLiNERAPI(ls.LitAPI):
    """
    GLiNERAPI is a subclass of ls.LitAPI that provides methods for the GLiNER model for entity recognition.

    Methods:
        - setup(device): Initializes the model and loads it onto the specified device.
        - decode_request(request): Extracts the input text and labels from the request.
        - predict(data): Generates a response based on the input text and labels.
        - encode_response(output): Encodes the generated response into a dictionary format.
    """

    def setup(self, device):
        """
        Sets up the GLiNER model for prediction.
        """
        # Load the GLiNER model from the Hugging Face model hub
        model_name = "knowledgator/modern-gliner-bi-large-v1.0"
        self.model = GLiNER.from_pretrained(model_name, max_len=2048).to(device)

    def decode_request(self, request):
        """
        Decodes the input request to extract the input text and labels.
        """
        # Extract the input text and labels from the request
        return request["text"], request.get("labels", [])

    def predict(self, data):
        """
        Generates a prediction based on the provided input text and labels.
        """
        # Use the model to predict the entities in the text with the given labels
        text, labels = data
        return self.model.predict_entities(text, labels, threshold=0.3)

    def encode_response(self, output):
        """
        Encodes the given results into a dictionary format.
        """
        # Return the entities in a dictionary format
        output = "\n".join(
            [
                f"- **{entity['label'].capitalize()}**: {entity['text']}"
                for entity in output
            ]
        )
        return {"entities": output}


if __name__ == "__main__":
    # Create an instance of the GLiNERAPI class and run the server
    api = GLiNERAPI()
    server = ls.LitServer(api, track_requests=True)
    server.run(port=5070)