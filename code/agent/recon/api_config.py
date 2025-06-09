"""
NOTE: You need to use your own api keys.
"""

import os
import json

# Load API keys from environment variables
gpt_api_key = os.environ.get("OPENAI_API_KEY", "")
claude_api_key = os.environ.get("ANTHROPIC_API_KEY", "")

# Load model from config.json
ts_temp = 1.0
model = "gpt-4o-mini"
ts_context = 4000
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
        model = config['agent']['model']
        ts_temp = config['agent']['typechat_temperature']
        ts_context = config['agent']['typechat_context_length']
except (FileNotFoundError, KeyError):
    print("Warning: config.json not found or missing 'agent.model' key. Defaulting to 'gpt-4o-mini'")
    model = "gpt-4o-mini"
    ts_temp = 1.0
    ts_context = 4000

typechat_temperature = ts_temp
typechat_context_length = ts_context

"""
NOTE: 
    The following models are used by ourselves in our paper. 
    You can change these models to meet your requirements.
"""

tokens_left_for_answer = 1500

gpt_3_5_model = model
gpt_3_5_long_context_model = model
# gpt_3_5_model = "llama3.2:3b"
# gpt_3_5_long_context_model = "llama3.2:3b"
gpt_3_5_short_model_context = 4000 - tokens_left_for_answer

# We can also use o1-mini
gpt_4_model = model
gpt_4_long_context_model = model
# gpt_4_model = "llama3.2:3b"
# gpt_4_long_context_model = "llama3.2:3b"
gpt_4_short_model_context = 8000 - tokens_left_for_answer

claude_model = "claude-2.0"
claude_short_model_context = 128000 - tokens_left_for_answer

"""
NOTE: If you have your own api_base_url, you can change the following urls to yours.
"""
gpt_api_base_url = "https://api.openai.com/v1/chat/completions"
# gpt_api_base_url = "http://localhost:21000/v1/chat/completions"
claude_api_base_url = "https://api.anthropic.com/v1/messages"


# TypeChat configuration
typechat_llm = "gpt-4o-mini"

typechat_schema_vote = "typechat_schemas/VotingSchema.ts"
typechat_schema_propose = "typechat_schemas/PartyProposalSchema.ts"
typechat_schema_talk = "typechat_schemas/TalkSchema.ts"
typechat_schema_quest = "typechat_schemas/QuestSchema.ts"
typechat_schema_assassin = "typechat_schemas/AssassinationSchema.ts"
typechat_schema_talk_revise_think = "typechat_schemas/TalkReviseThinkSchema.ts"
typechat_schema_talk_revise_speak = "typechat_schemas/TalkReviseSpeakSchema.ts"
