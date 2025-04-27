from threading import Thread

import litserve as ls
from litserve.specs.openai import ChatCompletionRequest
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)


class DeepSeekR1API(ls.LitAPI):
    def setup(self, device):
        self.device = device

        model_id = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id).to(self.device)

        self.streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )

    def decode_request(self, request: ChatCompletionRequest, context: dict):
        # Update context with generation arguments
        context["generation_args"] = {
            "temperature": request.temperature or 0.6,
            "max_new_tokens": request.max_completion_tokens or 1024,
        }

        # Prepare messages for tokenization
        messages = [
            message.model_dump(exclude_none=True) for message in request.messages
        ]

        # Tokenize messages and prepare input IDs
        inputs = self.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        ).to(self.device)

        # Return model inputs
        return inputs

    def predict(self, inputs: dict, context: dict):
        generation_kwargs = dict(
            **inputs,
            streamer=self.streamer,
            eos_token_id=self.tokenizer.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id,
            **context["generation_args"],
        )
        # Start generation in a separate thread
        generation_thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        generation_thread.start()

        # Yield generated text from the streamer
        for text in self.streamer:
            # print(f"\033[92m{text or ''}\033[0m", end="", flush=True)
            yield text

        # Ensure the generation thread has finished
        generation_thread.join()


if __name__ == "__main__":
    server = ls.LitServer(DeepSeekR1API(), spec=ls.OpenAISpec())
    server.run(port=5070)