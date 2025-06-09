import json
import re
import time
from typing import Dict, List, Optional

import openai
import requests
import tiktoken

from TypeChat.typechat.typechat import TypeChat, TypeChatResult
import api_config


def mark_memory_position(
    round_info: int,
    team_info: List[int] = None,
    mission_results_info: List[str] = None,
    mission_vote_results: List[List[str]] = None,
    previous_mission_player: List[List[str]] = None,
    previous_mission_leader: List[str] = None,
):
    if team_info is not None and len(team_info) > 0:
        team_info_str = f"The current proposed team players are: {', '.join([f'player {_}' for _ in team_info])}."
    else:
        team_info_str = f"The current proposed team players are: no proposed team."
    mission_results_info_str = f"The mission results in the history with corresponding team members is as follows:\n\n"
    print("Team Info Str:", team_info_str)
    if (
        mission_results_info is not None
        and len(mission_results_info) > 0
        and mission_vote_results is not None
    ):
        print("%" * 50)
        print(mission_results_info)  # ['fail']
        print(mission_vote_results)  # [] #TODO: check if we actually  need this?
        print(previous_mission_player)  # [['Sam', 'Kira'], []]
        print(previous_mission_leader)  # ['Mia', 'Paul']
        print("%" * 50)
        for i in range(1, len(mission_results_info) + 1):
            mission_results_info_str += f"The result of mission {i} in the history is: {mission_results_info[i - 1]}. The team members involved in this mission are {previous_mission_player[i - 1]}, and the proposed team leader is {previous_mission_leader[i - 1]}.\n"
    else:
        mission_results_info_str += "Empty."
    return {
        "current_round": f"The current round number is {round_info}.",
        "current_proposed_team_players": team_info_str,
        "current_mission_results": mission_results_info_str,
    }


def log_decorator(func):
    def wrapper(ref, subject, message):
        func(ref, subject, message)

        memory_status = mark_memory_position(
            round_info=ref.round,
            team_info=ref.proposed_team,
            mission_results_info=ref.round_result,
            mission_vote_results=ref.round_vote_result,
            previous_mission_player=ref.previous_player_team_list,
            previous_mission_leader=ref.previous_leader_list,
        )
        ref.memory_dict_list_append(memory_status)

    return wrapper


def judge_contents_valid(think_content, speak_content, is_first_think_then_speak):
    if is_first_think_then_speak:
        if not think_content.strip() or not speak_content.strip():
            return False
    else:
        if not speak_content.strip():
            return False
    return True


def extract_think_speak(
    action,
    config,
):
    if not config["is_first_think_then_speak"]:
        think_content = ""
        speak_content = action
        return think_content, speak_content

    think_lines = re.findall(
        r"(?:THINK:|Note:|\(Note:|NOTE:|\(NOTE:)(.*?)(?=END|SPEAK:|THINK:|Note:|\(Note:|NOTE:|\(NOTE:|$)",
        action,
        re.DOTALL,
    )
    speak_lines = re.findall(
        r"SPEAK:(.*?)(?=END|THINK:|SPEAK:|Note:|\(Note:|NOTE:|\(NOTE:|$)",
        action,
        re.DOTALL,
    )

    think_content = "\n".join(line.strip() for line in think_lines)
    speak_content = "\n".join(line.strip() for line in speak_lines)

    return think_content, speak_content


def extract_think_speak_in_revision(
    action,
    config,
):
    print(action)
    if config.is_first_think_then_speak:
        think_lines = re.findall(
            r"REVISED THINK:(.*?)(?=END|THINK:|SPEAK:|REVISED THINK:|REVISED SPEAK:|$)",
            action,
            re.DOTALL,
        )
        think_content = "\n".join(line.strip() for line in think_lines)
    else:
        think_content = ""

    speak_lines = re.findall(
        r"REVISED SPEAK:(.*?)(?=END|THINK:|SPEAK:|REVISED THINK:|REVISED SPEAK:|$)",
        action,
        re.DOTALL,
    )
    speak_content = "\n".join(line.strip() for line in speak_lines)

    return think_content, speak_content


def extract_plan_id(select_plans_prompt) -> int:
    match = re.search(r"The best plan is .*(\d+).*", select_plans_prompt)
    if match:
        return int(match.group(1)) - 1
    else:
        return None


def extract_speak_id(select_plans_prompt) -> int:
    match = re.search(r"The best speech is .*(\d+).*", select_plans_prompt)
    if match:
        return int(match.group(1)) - 1
    else:
        return None

def _tshelper_mergeMessages(input_messages):
    merged_input_messages = []
    is_system_prompt_now = True
    system_prompt = ""
    cur_user_prompt, cur_assistant_prompt = "", ""
    for message in input_messages:
        if message["role"] == "user":
            if len(cur_assistant_prompt) > 0:
                merged_input_messages.append(
                    {"role": "assistant", "content": cur_assistant_prompt}
                )
                cur_assistant_prompt = ""
            cur_user_prompt = cur_user_prompt + message["content"] + "\n\n\n"
        elif message["role"] == "assistant":
            if len(cur_user_prompt) > 0:
                merged_input_messages.append(
                    {"role": "user", "content": cur_user_prompt}
                )
                cur_user_prompt = ""
            cur_assistant_prompt = (
                cur_assistant_prompt + message["content"] + "\n\n\n"
            )
        else:
            raise ValueError(f"Invalid role: {message['role']}")
    if (len(cur_user_prompt) > 0 and len(cur_assistant_prompt) == 0):
        merged_input_messages.append({"role": "user", "content": cur_user_prompt})
    else:
        raise ValueError(f"The last prompt must be user!")
    return merged_input_messages

def call_typechat(
        system_prompt: Optional[str] = None,
        input_messages: Optional[List[Dict]] = None,
        config: Dict = None,
        schema: str = None):
    #
    ts = TypeChat()
    ts.createLanguageModel(model=api_config.typechat_llm, api_key=api_config.gpt_api_key, use_json_mode="4o" in api_config.typechat_llm, temperature=api_config.typechat_temperature, context_length=api_config.typechat_context_length)
    ts.loadSchema(schema)
    tns = ts.createJsonTranslator(
        name=schema.split("/")[-1].split(".")[0],
        basedir="./TypeChat/typechat/schemas"
    )
    input_messages = _tshelper_mergeMessages(input_messages)
    response = tns.translate(input_messages, image=None, return_query=False)
    if response.success:
        res = None
        if "vote" in response.data.keys():
            res = f"[{response.data['vote']}]"
        elif "party" in response.data.keys():
            res = ", ".join(response.data["party"])
        elif "think" in response.data.keys():
            res =  f"THINK: {response.data['think']} SPEAK: {response.data['speak']} END"
        elif "quest" in response.data.keys():
            res = f"[{response.data['quest']}]"
        elif "assassinate" in response.data.keys():
            res =  {response.data['assassinate']}
        elif "revised_think" in response.data.keys():
            res = f"REVISED THINK: {response.data['revised_think']} REVISED SPEAK: {response.data['revised_speak']} END"
        # elif "revise_speak" in response.data.keys():
        #     return f"REVISED SPEAK: {response.data['revise_speak']} END"
        return res, response
    return None, response

def call_api(
    system_prompt: Optional[str] = None,
    input_messages: Optional[List[Dict]] = None,
    config: Dict = None,
):

    merged_input_messages = []
    is_system_prompt_now = True
    system_prompt = ""
    cur_user_prompt, cur_assistant_prompt = "", ""
    for message in input_messages:
        if message["role"] == "system":
            if not is_system_prompt_now:
                raise ValueError("System prompt must be at the beginning")
            system_prompt = system_prompt + message["content"] + "\n\n\n"
        else:
            if is_system_prompt_now:
                merged_input_messages.append(
                    {"role": "system", "content": system_prompt}
                )
                is_system_prompt_now = False
                if message["role"] != "user":
                    raise ValueError(
                        "The first prompt after the system prompt must be user!"
                    )
            if message["role"] == "user":
                if len(cur_assistant_prompt) > 0:
                    merged_input_messages.append(
                        {"role": "assistant", "content": cur_assistant_prompt}
                    )
                    cur_assistant_prompt = ""
                cur_user_prompt = cur_user_prompt + message["content"] + "\n\n\n"
            elif message["role"] == "assistant":
                if len(cur_user_prompt) > 0:
                    merged_input_messages.append(
                        {"role": "user", "content": cur_user_prompt}
                    )
                    cur_user_prompt = ""
                cur_assistant_prompt = (
                    cur_assistant_prompt + message["content"] + "\n\n\n"
                )
            else:
                raise ValueError(f"Invalid role: {message['role']}")
    if (
        not is_system_prompt_now
        and len(cur_user_prompt) > 0
        and len(cur_assistant_prompt) == 0
    ):
        merged_input_messages.append({"role": "user", "content": cur_user_prompt})
    else:
        raise ValueError(f"The last prompt must be user!")

    if "gpt" in config["model_name"]:
        response = call_gpt_api(input_messages=merged_input_messages, config=config)
    elif "claude" in config["model_name"]:
        response = call_claude_api(input_messages=merged_input_messages, config=config)
    else:
        raise ValueError(f"Invalid model_name: {config['model_name']}!")

    return response.data, response


# call claude api
def call_claude_api(
    input_messages: Optional[List[Dict]] = None,
    config: Dict = None,
    temperature: float = None,
):
    if input_messages is None:
        raise ValueError("messages should not be None!")

    temperature = config["temperature"]
    max_tokens = config["max_tokens"] if "max_tokens" in config else None
    n = config["n"] if "n" in config else 1
    stop = config["stop"] if "stop" in config else None
    seed = config["seed"] if "seed" in config else None

    message = get_forward_response(
        model=api_config.claude_model,
        messages=input_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=n,
        stop=stop,
        seed=seed,
        model_type="claude",
    )

    return message


def call_gpt_api(
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    input_messages: Optional[List[Dict]] = None,
    config: Dict = None,
):
    if system_prompt is None or user_prompt is None:
        if input_messages is None:
            raise ValueError("Invalid empty messages!")
    else:
        if input_messages is not None:
            raise ValueError("messages should be None!")

    model = config["long_context_model"]

    # encoding = tiktoken.encoding_for_model(config['short_context_model'])
    # Small hack to get a sufficient encoding for the model
    encoding = tiktoken.encoding_for_model("gpt-4o-mini")
    if input_messages is None:
        tokens_integer = encoding.encode(user_prompt)
    else:
        messages_str = ""
        for dict_item in input_messages:
            for key, item in dict_item.items():
                messages_str += f"{key}: {item}"
        tokens_integer = encoding.encode(messages_str)

    if len(tokens_integer) > config["short_model_context"]:
        model = config["long_context_model"]
    else:
        model = config["short_context_model"]

    openai.api_key = api_config.gpt_api_key

    temperature = config["temperature"]
    max_tokens = config["max_tokens"] if "max_tokens" in config else None
    n = config["n"] if "n" in config else 1
    stop = config["stop"] if "stop" in config else None
    seed = config["seed"] if "seed" in config else None
    # Call OpenAI API to generate a message based on the prompt
    if "gpt-3.5" in model:
        message = get_forward_response(
            model=model,
            messages=(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                if input_messages is None
                else input_messages
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            n=n,
            stop=stop,
            seed=seed,
            model_type="gpt-3.5",
        )
    elif "gpt-4" in model:
        message = get_forward_response(
            model=model,
            messages=(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                if input_messages is None
                else input_messages
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            n=n,
            stop=stop,
            seed=seed,
            model_type="gpt-4",
        )
    elif "llama" in model:
        input_message = (
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            if input_messages is None
            else input_messages
        )
        # print(input_message)
        message = get_forward_response(
            model=model,
            messages=input_message,
            temperature=temperature,
            max_tokens=max_tokens,
            n=n,
            stop=stop,
            seed=seed,
            model_type="gpt-4",
        )
    elif "o1" in model:
        message = get_forward_response(
            model=model,
            messages=(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                if input_messages is None
                else input_messages
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            n=n,
            stop=stop,
            seed=seed,
            model_type="o1",
        )
    else:
        raise ValueError(f"Invalid model: {model}")

    return message


global_counter = 0


def get_forward_response(
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: int,
    n: int,
    stop,
    seed: int,
    model_type: str,
) -> str:
    # Set up the API URL and headers based on model type
    if model_type in ["gpt-3.5", "gpt-4", "o1"]:
        url = api_config.gpt_api_base_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_config.gpt_api_key}",  # Bearer added for correct authorization
        }
    elif model_type == "claude":
        url = api_config.claude_api_base_url
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": api_config.claude_api_key,
        }
    else:
        raise ValueError(f"Invalid model type: {model_type}")

    # Prepare the data payload for the request
    data = {
        "model": model,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stop": stop,
        "n": n,
        "seed": seed,
    }

    if model_type in ["o1"]:
        # Rename/Remove some fields for the O1 model
        data["max_completion_tokens"] = data["max_tokens"]
        del data["max_tokens"]
        del data["stop"]
        # In the messages, we need to update the system role field to user
        for message in data["messages"]:
            if message["role"] == "system":
                message["role"] = "user"

    # Attempt to send the request, retrying up to 5 times on failure
    try_num = 0
    while True:
        try_num += 1
        if try_num > 5:
            raise ValueError("Too many failed attempts to call the API!")

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                print(response.content.decode())
                print(f"{response.status_code=}")
                time.sleep(5)  # Wait before retrying
                continue
            else:
                break
        except Exception as e:
            print(f"Error during API call: {e}")
            time.sleep(5)
            continue

    # Parse the response and extract the content
    response_json = response.json()
    agent_response = response_json["choices"][0]["message"]["content"]

    result = TypeChatResult()

    ## converting to TypeChat response format here to make it easier to deal with the data after
    result.success = True
    result.data = agent_response
    response.message = ""
    result.prompt = data["messages"]
    result.raw_response = response_json["choices"][0]["message"]["content"]
    result.usage = {"prompt_tokens": response_json["usage"]["prompt_tokens"], "completion_tokens": response_json["usage"]["completion_tokens"]}
    

    # Let's pretty-print the data payload for debugging
    # Save it to a file for debugging
    global global_counter
    global_counter += 1
    data["messages"].append({"role": "assistant", "content": agent_response})
    with open(f"data_payload_{global_counter}.json", "w") as f:
        f.write(json.dumps(data, indent=2))

    return result
