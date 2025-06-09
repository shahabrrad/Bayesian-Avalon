# This file has the LLM backend code. For now, this is a simple local LLM
import transformers
import uvicorn
import socket
import torch
from pydantic import BaseModel
import json

from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
from transformers import AutoModelForCausalLM, AutoTokenizer


# Initialize some variables
MODEL_ID = "mistralai/Mixtral-8x7B-Instruct-v0.1"
# MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"

class LLMBackend():
    def __init__(self):
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self._model = AutoModelForCausalLM.from_pretrained(MODEL_ID, attn_implementation="flash_attention_2", load_in_4bit=True)
        # self._model = AutoModelForCausalLM.from_pretrained(MODEL_ID)

    def inference(self, prompts):
        inputs = self._tokenizer.apply_chat_template(prompts, return_tensors="pt").to(0)
        outputs = self._model.generate(inputs, max_new_tokens=256)
        return self._tokenizer.decode(outputs[0], skip_special_tokens=True)

backend = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global backend
    backend = LLMBackend()

    # Now wait for shutdown
    yield

    # No cleanup needed...
    pass

# Defines the FastAPI app
app = FastAPI(lifespan=lifespan)

class LLMPrompt(BaseModel):
    prompts: list

# This is the single-turn example for Starling. 
@app.post("/api/")
def generate_response(prompt: LLMPrompt):
    global backend
    response = backend.inference(prompt.prompts)
    response = response.split("[/INST]")[-1]

    # res = Response(
    #     {
    #         "response": response,
    #     },
    #     media_type="application/json"
    # )
    return response

# This is the main function that starts the agent manager
if __name__ == "__main__":
    local_ip = socket.gethostbyname(socket.gethostname())
    uvicorn.run(app, host=local_ip, port=23004)