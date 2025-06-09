import requests
import json

LLM_SERVER = "http://localhost:23004/api/"

def generate_response(prompt):
    response = requests.post(LLM_SERVER, json={"prompts": prompt})
    return response.text

if __name__ == "__main__":
    messages = [
        {"role": "user", "content": "What is your favourite condiment?"},
        {"role": "assistant", "content": "Well, I'm quite partial to a good squeeze of fresh lemon juice. It adds just the right amount of zesty flavour to whatever I'm cooking up in the kitchen!"},
        {"role": "user", "content": "Do you have mayonnaise recipes?"}
    ]
    result = generate_response(messages)
    print(result)