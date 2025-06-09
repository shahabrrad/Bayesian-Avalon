import streamlit as st
import requests
import json
import pandas as pd
import socket

def getListOfGames():
    st.session_state.game_ids = {}
    try:
        response = requests.get(st.session_state.game_server_api, json={"action": "get_games"})
    except requests.exceptions.ConnectionError:
        st.toast("Failed to connect to game server", icon='🔥')
        return
    response = json.loads(response.text)
    if response["status"] != "success":
        st.toast(f"Failed to gather game list: {response['message']}", icon='🔥')
        return
    print("Got list of games", response["data"])
    st.session_state.game_ids = response["data"]

def updatePlayerData():
    st.session_state.player_data = pd.DataFrame(columns=["Name", "Type", "Role"])
    for plr in st.session_state.game_ids[st.session_state.game_id]["players"]:
        st.session_state.player_data.loc[len(st.session_state.player_data.index)] = [plr["hname"], plr["type"], plr["role"]]
    print(st.session_state.player_data)

def addAgent():
    response = requests.get(st.session_state.agent_api + "/startup/", params={"game_id": st.session_state.game_id, "agent_type": st.session_state.agent_type, "agent_role_preference": st.session_state.agent_role_preference})
    response = json.loads(response.text)
    if response["success"]:
        st.toast(f"Successfully added agent {response['agent_id']}", icon='🤖')
    else:
        st.toast(f"Failed to add agent: {response['message']}", icon='🔥')

def getAgentNames():
    return [plr["hname"] for plr in st.session_state.game_ids[st.session_state.game_id]["players"] if "Agent:" in plr["type"]]

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]

    if "game_ids" not in st.session_state:
        st.session_state.game_ids = {}
    if "game_server_api" not in st.session_state:
        st.session_state.game_server_api = f"http://{local_ip}:23001/api"
    if "agent_api" not in st.session_state:
        st.session_state.agent_api = f"http://{local_ip}:23003/api"
    if "player_data" not in st.session_state:
        st.session_state.player_data = pd.DataFrame(columns=["Name", "Type", "Role"])

    getListOfGames()

    st.sidebar.markdown("# Agent Manager")
    st.sidebar.selectbox("Select Game", st.session_state.game_ids.keys(), key="game_id")
    st.sidebar.markdown("### Configuration")
    st.sidebar.text_input("Game Server API", value=st.session_state.game_server_api, on_change=getListOfGames)
    st.sidebar.text_input("Agent API", value=st.session_state.agent_api)

    if st.session_state.game_id:
        st.markdown(f"## Manage Game: {st.session_state.game_id} ({st.session_state.game_ids[st.session_state.game_id]['status']})")

        updatePlayerData()

        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown("### Players")
            st.dataframe(st.session_state.player_data, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("### Agents")
            # st.selectbox("Agent Type", ["ab", "acl", "test"], key="agent_type")
            st.selectbox("Agent Type", ["acl"], key="agent_type")
            st.selectbox("Agent Role", ["random", "good", "evil"], key="agent_role_preference")
            if st.button("Add Agent", use_container_width=True):
                addAgent()

        st.markdown("### Agent's Game State")
        st.selectbox("Agent", getAgentNames(), key="agent_name")

        st.sidebar.markdown("### Agent Manager Utilization")
        st.sidebar.markdown("LLM Pending Queries: 0")
        st.sidebar.markdown("LLM Workers: 0")
        