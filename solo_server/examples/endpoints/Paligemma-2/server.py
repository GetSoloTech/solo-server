# Import the required libraries
import os
from dotenv import load_dotenv
import torch
from transformers import PaliGemmaProcessor, PaliGemmaForConditionalGeneration
from transformers.image_utils import load_image
import litserve as ls


# Load the Environment Variables from .env file
load_dotenv()

# Access token for using the model
access_token = os.environ.get("ACCESS_TOKEN")


class PaliGemma2API(ls.LitAPI):
    """
    PaliGemma2API is a subclass of ls.LitAPI that provides an interface to the PaliGemma2 family of models.

    Methods:
        - setup(device): Initializes the model and processor with the specified device.
        - decode_request(request): Convert the request payload to model input.
        - predict(model_inputs): Uses the model to generate a caption for the given input image and language.
        - encode_response(output): Convert the model output to a response payload.
    """

    def setup(self, device):
        """
        Sets up the model and processor on the specified device.
        """
        model_id = "google/paligemma2-3b-ft-docci-448"
        self.device = device
        self.model = (
            PaliGemmaForConditionalGeneration.from_pretrained(
                model_id, torch_dtype=torch.bfloat16, token=access_token
            )
            .eval()
            .to(self.device)
        )
        self.processor = PaliGemmaProcessor.from_pretrained(
            model_id, token=access_token
        )

    def decode_request(self, request):
        """
        Convert the request payload to model input.
        """
        # Extract the image path and language from the request
        image = load_image(request["image_path"])
        language = request.get("language", "en")

        # Prepare the prompt for the caption generation
        prompt = f"<image>caption {language}"

        # Prepare the model inputs
        return (
            self.processor(text=prompt, images=image, return_tensors="pt")
            .to(torch.bfloat16)
            .to(self.model.device)
        )

    def predict(self, model_inputs):
        """
        Run inference and generate caption based on the provided model inputs.
        """
        input_len = model_inputs["input_ids"].shape[-1]

        # Generate the response using the model
        with torch.inference_mode():
            generation = self.model.generate(
                **model_inputs, max_new_tokens=100, do_sample=False
            )
            generation = generation[0][input_len:]
            return self.processor.decode(generation, skip_special_tokens=True)

    def encode_response(self, output):
        """
        Convert the model output to a response payload.
        """
        return {"caption": output}


if __name__ == "__main__":
    # Create an instance of the PaliGemma2API class and run the server
    api = PaliGemma2API()
    server = ls.LitServer(api, track_requests=True)
    server.run(port=5070)