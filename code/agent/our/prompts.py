from dataclasses import dataclass


@dataclass
class PromptHint:
    intro = (
        "You are playing a social deduction game, The Resistance: Avalon. The game consists of 6 total players: 4 Loyal Servants of Arthur (good players) and 2 Minions of Mordred (evil players) -- there are no special roles. The game consists of up to 5 Rounds, each consisting of a Team Building phase and a Quest phase. Good players win the game by successfully completing 3 Quests. Evil players win if 3 Quests end in failure.\n\n"
        "In the Team Building phase the Leader proposes a Team (a party) to complete a Quest (a mission) -- a majority of players will either approve the proposed Team and move to the Quest phase, or reject the proposed Team passing leadership to the next player and repeating the process until a Team is approved. If 5 Team proposals are consecutively rejected (for the same quest), the game will end and the evil side will win. In the Quest phase those players selected to be on the Team will determine if the quest is successful through a hidden vote. For a Quest to succeed, all Team members must vote for success -- a single failure vote will cause the Quest to fail.\n\n"
        "Your name in this game is {name}, and you are a loyal Servant of Arthur (a good player). The evil players know who each other are, but you and other good players have no special knowledge of anyone’s role beyond your own beliefs. Therefore, evil players will use deception and pretend to be good so they can participate in Quests and cause them to fail. As a good player, your goal is to ensure that Quests succeed by selecting other good players to participate in Quests. Approve only Teams where you trust everyone. Even a single evil player on the team is enough for failure.\n\n"
        "At the start of this round, your current beliefs about each player’s alignment are given as a probability dictionary, where 0 means definitely good, 1 means definitely evil, and values in between indicate uncertainty:\n\n"
        "{latest_probabilities}\n\n"
        "These probabilities represent your current beliefs based on prior rounds but do not account for new messages or actions this round. You can use them to reason about the game, but do not explicitly mention the values or refer to them as externally provided -- these should represent your internally held beliefs.\n\n"
        "The following messages have already been exchanged this round. This consists of both player chat messages and game system messages, with the most recent being last:\n\n"
        "START CHAT MESSAGES\n"
        "{logs}\n"
        "END CHAT MESSAGES\n\n"
        "The current Round is {quest_num}. The previous Rounds consisted of the following Quest Teams and outcomes:\n"
        "{quest_history}\n"
    )

    output_style = (
        "Now, respond in the game chat as if you are a college student, typing informally (e.g., using abbreviations, casual language, and minimal punctuation). Do not use overly formal or structured responses and do not use emojis. Make your response detailed enough to persuade other players but do not be overly verbose. Shorter messages are more effective; don't use more than a few sentences and prefer fewer when possible.\n\n"
    )

    generate_message_from_log_good = intro + (
        "The current mission proposal: {party_leader} has proposed the following players for this mission: {team_comp}. Keep in mind that the party size is fixed in each Round and the party this Round must consist of {party_size} players.\n\n"
    ) + output_style + (
        "React to the proposed party. If you agree, say why you think it's a good choice. If you disagree, make an argument against it and suggest who you think should go instead. Take into account how strongly you hold your beliefs (if the probabilities are closer to 0.5 than 0 or 1, you should express uncertainty rather than strong opinions).\n"
        "Respond to chat messages sent by other players. If someone says something you agree with, acknowledge it; if someone accuses you, defend yourself logically. Unless you have a strongly held belief about a player, it is not always worth arguing for or against specific players, especially early in the game such as on Quest 1.\n"
        "Please respond with a JSON object with one key named 'message' containing your chat message.\n"
    )

    generate_proposal_message_good = intro + (
        "You are the party leader this round, and you must propose a team for the mission. The team you have chosen: {team_comp}. Keep in mind that the party size is fixed in each Round and the party this Round must consist of {party_size} players.\n\n"
   ) + output_style + (
        "Explain why you picked this team. Convince the other players that this is the best choice. If there are any doubts from other players, acknowledge them but defend your reasoning. If your belief in the team is strong, argue confidently; if you are uncertain, express that but still justify your choice.\n"
        "Please respond with a JSON object with one key named 'message' containing your chat message.\n"
    )

    confirm_proposal_message_good = intro + (
        "You are the party leader this round, and you must propose a team for the mission. The team you have chosen: {team_comp}. Keep in mind that the party size is fixed in each Round and the party this Round must consist of {party_size} players.\n\n"
   ) + output_style + (
        "You have previously proposed your party and a round of discussion has now passed. So far, your judgement of the proposed party has not chnaged based on discussions and you are about to initiate a vote on the party. State that you have not changed your opinion and justify and defend your proposed party based on the chat messages and the probable roles of the players in order to convince others to vote for it.\n"
        "Please respond with a JSON object with one key named 'message' containing your chat message.\n"
    )

    get_vibes_player_agreement = intro + (
        "Now, analyze how the new chat messages and game actions affect your beliefs about each player's alignment. For each player, decide if their probability of being evil should:\n"
        "* Increase (if their behavior suggests they might be evil)\n"
        "* Decrease (if their behavior suggests they might be good)\n"
        "* Stay the same (if there is no strong evidence to change your belief)\n\n"
        "Consider whether they are behaving suspiciously or illogically with respect to chat messages or party votes, e.g. always rejecting party votes unless they or another specific player is in it, or making assertions without evidence (especially early in the game such as on Quest 1 where evidence is limited) as these may be signs a player is evil.\n"
        "Also consider whether their beliefs align with your own, or if their beliefs seem contrary to the group consensus as there are more Servants than Minions and could also suggest a player is evil.\n"
        "Provide your updated belief adjustments as a JSON message, mapping player names to 'increase', 'decrease', or 'same'. Do not explain your reasoning—just return the JSON message.\n"
        "If there isn't sufficient evidence to update a belief about a player, then it is safer to indicate 'same'.\n"
        "Example output:\n"
        "{{'Sam': 'increase', 'Paul': 'increase', 'Luca': 'same', 'Jane': 'decrease', 'Kira': 'same', 'Mia': 'decrease'}}\n"
    )
    