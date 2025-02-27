import litserve as ls
import torch
import tensorflow as tf

# Define a PyTorch model
class PyTorchModel(torch.nn.Module):
    def forward(self, x):
        return x * 2

# Define a TensorFlow model
class TensorFlowModel(tf.Module):
    @tf.function(input_signature=[tf.TensorSpec(shape=None, dtype=tf.float32)])
    def __call__(self, x):
        return x + 3

# (STEP 1) - DEFINE THE API
class ComplexLitAPI(ls.LitAPI):
    def setup(self, device):
        # Setup is called once at startup. Load multiple models and initialize resources.
        self.model1 = PyTorchModel().to(device)  # Load PyTorch model
        self.model2 = TensorFlowModel()  # Load TensorFlow model

    def decode_request(self, request):
        input_data = request["input"]
        transformed_data = input_data / 2
        return transformed_data

    def predict(self, x):
        # Run inference through both models and combine their outputs.
        output1 = self.model1(torch.tensor(x)).item()  # Run PyTorch model
        output2 = self.model2(tf.constant(x)).numpy()  # Run TensorFlow model
        combined_output = output1 + output2  # Combine outputs from both models
        return {"output": combined_output}

    def encode_response(self, output):
        # Convert the model output to a response payload.
        return {"final_output": output}

# (STEP 2) - START THE SERVER
if __name__ == "__main__":
    # Scale with advanced features (batching, GPUs, etc...)
    server = ls.LitServer(ComplexLitAPI(), accelerator="auto", max_batch_size=2, batch_timeout=0.10)
    server.run(port=5070)