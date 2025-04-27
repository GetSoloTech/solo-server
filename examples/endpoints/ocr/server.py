# Import necessary libraries
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText
import litserve as ls


class OCR2API(ls.LitAPI):
    """
    OCR2API is a subclass of ls.LitAPI that provides an interface to the GOT-OCR2.0 model for various OCR tasks.

    Methods:
        - setup(device): Called once at startup for the task-specific setup.
        - decode_request(request): Convert the request payload to model input.
        - predict(inputs): Uses the model to generate OCR text from the input image.
        - encode_response(output): Convert the model output to a response payload.
    """

    def setup(self, device):
        """
        Set up the OCR model for the task.
        """
        # Set up model and specify the device
        self.device = device
        self.model = AutoModelForImageTextToText.from_pretrained(
            "stepfun-ai/GOT-OCR-2.0-hf", device_map=self.device
        )
        self.processor = AutoProcessor.from_pretrained("stepfun-ai/GOT-OCR-2.0-hf")

    def decode_request(self, request):
        """
        Convert the request payload to model input.
        """
        # Extract the image path and color from the request
        image_path = request.get("image_path")
        color = request.get("color", None)

        # Load the image from the path
        image = Image.open(image_path)

        # Prepare the model input by processing the image
        return self.processor(image, return_tensors="pt", color=color).to(self.device)

    def predict(self, inputs):
        """
        Run inference and get the model output.
        """
        # Run inference on the image to get the text output
        with torch.inference_mode():
            generate_ids = self.model.generate(
                **inputs,
                do_sample=False,
                tokenizer=self.processor.tokenizer,
                stop_strings="<|im_end|>",
                max_new_tokens=4096
            )
            return self.processor.decode(
                generate_ids[0, inputs["input_ids"].shape[1] :],
                skip_special_tokens=True,
            )

    def encode_response(self, output):
        """
        Convert the model output to a response payload.
        """
        # Return the text output in the response
        return {"text": output}


if __name__ == "__main__":
    # Create an instance of the OCR2API and run the server
    api = OCR2API()
    server = ls.LitServer(api, track_requests=True)
    server.run(port=5070)