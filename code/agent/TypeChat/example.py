from typechat.typechat import TypeChat
from keys import API_KEY, ORG_KEY

# This is for selection of what backend you want to use
# Please only use one of them at a time
USE_OPENAI = False
USE_FASTCHAT = False
USE_OLLAMA = True

def customCallback():
    return {}

if __name__ == "__main__":
    # First, create a TypeChat instance
    ts = TypeChat()

    # Set up the language model that you want to use
    # Note: If you are utilizing local LLMs (e.g. through FastChat), you can set base_url to the URL of your local LLM
    # Note: You can enable json_mode if you want, however, only gpt-4-1106-preview supports this
    if USE_OPENAI:
        # OpenAI requires an API key and an optional organization key
        ts.createLanguageModel(model="gpt-4", api_key=API_KEY, org_key=ORG_KEY)
    elif USE_FASTCHAT:
        # FastChat requires a base_url
        ts.createLanguageModel(model="Llama-2-13b-chat-hf", base_url="http://localhost:23002/v1")
    elif USE_OLLAMA:
        # You need to install Ollama and run it first (serve the model).
        ts.createLanguageModel(model="gemma:2b", base_url="http://localhost:11434/api/chat", use_ollama=True)
    else:
        print("Please select a backend to use")
        exit(1)
    
    # Load the schema that you want to use. Here, we use a simple TypeScript schema for sentiment analysis:
    ts.loadSchema("./typechat/schemas/sentimentSchema.ts")

    # Create a translator for the schema: The name is the name of your interface defined in your schema
    tns = ts.createJsonTranslator(name="SentimentResponse")

    # There are two ways to query the model:
    # 1. You can use a simple string object as your prompt. This will automatically be converted into a single user message
    request = "I'm having a good day"
    # 2. You can use a list of prompts for longer discussions.
    #    Note: This HAS to start and end with a user message
    #    Note: User and Assistant messages have to alternate
    #    Note: You can not use system messages in this as TypeChat is already occupying that role
    request = [
        {"role": "user", "content": "Hello, how are you?"}, 
        {"role": "assistant", "content": "I am great, how can I help you today?"},
        {"role": "user", "content": "I am having a good day so far and would like to know about llamas!"}
    ]
    # And finally, call the translate method
    # There are a few optional parameters:
    # - image: If you want to use an image model, you can provide an image (This is for GPT-4-Vision)
    # - return_query: If you want to return the query that was sent to the model, set this to True (this will not actually run the query)
    response = tns.translate(request, image=None, return_query=False)
    # The response object has a few fileds:
    # - success: True if the request was successful
    # - data: The response data
    # - error: The error message, if any
    if response.success:
        # The response data is a dictionary with the keys being the names of the fields in your schema
        print("The sentiment is", response.data["sentiment"])
        print("The confidence is", response.data["confidence"])
    else:
        print("Error:", response.message)