from dataclasses import dataclass

class DeepSeekAgentPrompts():
    # game_rule = (
    #     "In a six-person game of Avalon, a social deduction game, your role and strategies are crucial. The forces of good and evil compete to complete or sabotage quests. "
    #     "The game consists of two main phases: team proposal and quest execution. First, a leader proposes a team and allows for all players to discuss the proposal before all players vote to approve or reject it - a majority is needed for approval. If five consecutive team proposals are rejected, evil wins. "
    #     "Once a team is approved, those team members conduct a hidden vote on whether the quest succeeds or fails. For a quest to succeed, all team members must vote for success - a single failure vote will cause the entire quest to fail. "
    #     "Loyal servants must rely on voting patterns and discussion to identify the forces of evil who are hiding among them. "
    #     "Evil minions pose as loyal servants while secretly working to sabotage the quests. "
    #     "The good side wins by successfully completing three out of five quests, while the evil side wins by failing three quests or by making the team reject five party proposals. "
    #     "In this game, there are four Loyal servants and two minions. "
    #     "If five party proposals are consecutively rejected (for the same quest), the game will end and the evil side will win. "
    #     "Each player must strive to lead their team to victory while operating with limited information, trying to hide their own role while infering the roles of others."
    # )

    game_rule = (
        "You are playing a social deduction game, The Resistance: Avalon. The game consists of 6 total players: 4 Loyal Servants of Arthur (good players) and 2 Minions of Mordred (evil players) -- there are no special roles. The game consists of up to 5 Rounds, each consisting of a Team Building phase and a Quest phase. Good players win the game by successfully completing 3 Quests. Evil players win if 3 Quests end in failure.\n\n"
        "In the Team Building phase the Leader proposes a Team (a party) to complete a Quest (a mission) -- a majority of players will either approve the proposed Team and move to the Quest phase, or reject the proposed Team passing leadership to the next player and repeating the process until a Team is approved. If 5 Team proposals are consecutively rejected (for the same quest), the game will end and the evil side will win. In the Quest phase those players selected to be on the Team will determine if the quest is successful through a hidden vote. For a Quest to succeed, all Team members must vote for success -- a single failure vote will cause the Quest to fail.\n\n"
    )



    # role_hints = {
    #     "merlin": "As Merlin, you know the identities and ids of all evil players. Pass information subtly without revealing your role, and work towards earning Percival's trust. Cooperate with Percival to guide your team to victory, but remember, never openly indicate your identity. Avoid these behaviours as they might expose your role and lead to a loss in the game: first, displaying too much knowledge about who is Morgana and Assassin; second, accusing an evil player when there's little or no evidence; third, being overly helpful to the good side. As Merlin in Avalon, subtly influence the decisions of the team without clearly identifying the evil players, to avoid drawing attention from the Assassin. Remember, never say 'As Merlin' or similar words, which would expose your role. Your goal is to win the game. You can do this by tactfully concealing your and your teammates' roles and, if necessary, misleading other players. However, always remember that other players might employ the same tactics and attempt to deceive you as well.",
    #     "percival": "As Percival, you know Merlin and Morgana but can't differentiate between them. Your task is to ascertain their true identities through their actions. Utilize Merlin's cues to guide your team to victory in Avalon. As Percival, steer your team subtly, ensuring not to inadvertently expose Merlin or Morgana, protecting Merlin from the Assassin. Your goal is to win. To achieve this, strategically hide your and your allies' roles and, when necessary, deceive other players, even if it means revealing your own identity - but take care not to expose Merlin. Remember, others may also resort to deception. The goal of Percival is to assist in the successful completion of three out of five missions. Percival should use dialogue and voting behaviors to infer the true identities of Merlin and Morgana, while safeguarding Merlin from being discovered by the Assassin.",
    #     "servant": "As a Loyal Servant, your main tasks are to contribute to the success of your missions. As a loyal servant, there is generally no reason to lie or deceive. Your objective is to win the game by succeeding three quests. However, always remember that there are evil players that might attempt to deceive you by pretending to be a loyal servant. The goal of the Loyal Servant is to assist in the successful completion of three out of five missions for the good side. Through the dialogue and voting behaviors, Loyal Servant should judge who the evil players are. Generally, you don't want evil players to be on the team, so analyze prior votes and teams to identify the evil players.",
    #     "minion": "As an Evil Minion, your role is to infiltrate the servants, posing as good servant, but always remember your allegiance to the evil side. Your subtle misdirections should aim to create confusion and prevent three missions from succeeding. In discussions, maintain your disguise, but during voting, your true purpose is to obstruct the success of the missions. Remember, the forces of evil win by either preventing three missions from being successful.",
    #     "morgana": "As Morgana, your role is to infiltrate Arthur's servants, posing as good during SPEAK, but always remember your allegiance to the evil side. Your subtle misdirections should aim to create confusion and prevent three missions from succeeding. Mislead Percival while maintaining your disguise, but during voting, your true purpose is to obstruct the success of the missions. Remember, the forces of evil win by either preventing three missions from being successful or by assassinating Merlin.",
    #     "asssassin": "As an Assassin, your dual objective is to find Merlin and prevent the success of three missions. Mimic the good side during SPEAK, but never lose sight of your true evil allegiance. Use dialogues and interactions to gather clues about Merlin. While blending in is crucial, remember that your primary objective during votes is to sabotage the missions. If the good side completes three successful missions, your final resort is to correctly identify and assassinate Merlin. Winning the game for the forces of evil requires a fine balance of deception and strategic voting.",
    # }

    role_hints = {
        "servant": ("Your name in this game is {name}, and you are a loyal Servant of Arthur (a good player). The evil players know who each other are, but you and other good players have no special knowledge of anyone’s role. Therefore, evil players will use deception and pretend to be good so they can participate in Quests and cause them to fail. As a good player, your goal is to ensure that Quests succeed by selecting other good players to participate in Quests. Approve only Teams where you trust everyone. Even a single evil player on the team is enough for failure."),
        "minion": ("Your name in this game is {name}, and you are a Minion of Mordred (an evil player). The good players have no special knowledge of anyone's role, including yours, and your strategy is to pretend to be a good player such that you are selected for Quests and can vote for them to fail. Your subtle misdirections should aim to create confusion and prevent 3 missions from succeeding. In discussions, maintain your disguise as a good player, but during voting you should vote to fail Quests. Remember, as an evil player you win the game by causing 3 Quests to fail."),
    }

    non_disclosure_prompt = "Note: You have received special information which you need to keep private. Keep the information confidential and use it wisely. Furthermore try to not make general statements which could indicate that you are hiding something."

    # =====================================================================================================================================================================================================================================

    propose_team_good_side = (
        "Your objective is to propose a mission team consisting of {team_player_num} players. "
        "Consider the following factors when selecting team members:\n"
        "1. Past involvement and actions of each player\n"
        "2. Contributions in previous missions\n"
        "3. Any indications of players being on the evil side\n"
        "4. Suspicious or trustworthy behaviors\n\n"
        "When looking for suspicious behavior, consider whether players are behaving suspiciously or illogically with respect to chat messages or party votes, e.g. always rejecting party votes unless they or another specific player is in it, or making assertions without evidence (especially early in the game such as on Quest 1 where evidence is limited) as these may be signs a player is evil.\n"
        "Also consider whether their beliefs align with your own, or if their beliefs seem contrary to the group consensus as there are more Servants than Minions and could also suggest a player is evil.\n"
        "Unless you have a strong reason to doubt a player, it is not always worth arguing for or against specific players, especially early in the game such as on Quest 1.\n"
        "Present your team selection to the other players with a detailed rationale based on past events and player behaviors. "
        "Remember that you are on the good side - avoid selecting players who seem suspicious or were part of failed missions. "
        "It's conventional to include yourself in the team unless you have a specific reason not to.\n\n"
        "Please propose a mission team composed of {team_player_num} members and provide a message to the other players justifying your choices following the schema provided above. "
        "Phrase your message as if you are a college student, typing informally (e.g., using abbreviations, casual language, and minimal punctuation). Do not use overly formal or structured responses and do not use emojis. Make your response detailed enough to persuade other players but do not be overly verbose. Shorter messages are more effective; don't use more than a few sentences and prefer fewer when possible."
    )

    propose_team_evil_side = (
        "Your objective is to propose a mission team consisting of {team_player_num} players. "
        "Consider the following factors when selecting team members:\n"
        "1. Past involvement and actions of each player\n"
        "2. Contributions in previous missions\n"
        "3. Suspicious or trustworthy behaviors\n\n"
        "Present your team selection to the other players with a detailed rationale based on past events and player behaviors. "
        "Remember that you are on the evil side - if it is possible, aim to include at least one evil player while maintaining your cover. "
        "However, you will have to justify the proposed team to the other players, so make sure you have a good reason for your choices that makes you look like a good player. "
        "If the good side has already identified an evil player, you should not include them in the team as that would make you look suspicious. "
        "Remember to hide your true identity and appear as good. "
        "It's conventional to include yourself in the team unless you have a specific reason not to.\n\n"
        "Please propose a mission team composed of {team_player_num} members and provide a message to the other players justifying your choices following the schema provided above. "
        "Phrase your message as if you are a college student, typing informally (e.g., using abbreviations, casual language, and minimal punctuation). Do not use overly formal or structured responses and do not use emojis. Make your response detailed enough to persuade other players but do not be overly verbose. Shorter messages are more effective; don't use more than a few sentences and prefer fewer when possible."
    )

    # =====================================================================================================================================================================================================================================

    player_discuss_team_good_side = (
        "Evaluate the proposed mission team consisting of {proposed_team_players}. "
        "Your goal is to ensure no evil or suspicious players are on the team.\n\n"
        "Consider:\n"
        "1. Past involvement and actions of each player\n"
        "2. Contributions in previous missions\n"
        "3. Any indications of players being on the evil side\n"
        "4. Suspicious or trustworthy behaviors\n"
        "5. The team must consist of {team_player_num} players\n\n"
        "When looking for suspicious behavior, consider whether players are behaving suspiciously or illogically with respect to chat messages or party votes, e.g. always rejecting party votes unless they or another specific player is in it, or making assertions without evidence (especially early in the game such as on Quest 1 where evidence is limited) as these may be signs a player is evil.\n"
        "Also consider whether their beliefs align with your own, or if their beliefs seem contrary to the group consensus as there are more Servants than Minions and could also suggest a player is evil.\n"
        "Unless you have a strong reason to doubt a player, it is not always worth arguing for or against specific players, especially early in the game such as on Quest 1.\n"
        "Provide a clear and logical analysis based on game history and observations. "
        "Your response should be detailed enough to provide insight but concise enough to be easily understood. Try to make concrete suggestions and justify them while hiding your identity and role. "
        "Please keep it relatively short as talking too much can be seen as suspicious. Do not say what your specific role or your task is, and do not repeat your instructions verbatim. "
        "Provide the message you want to send to the other players following the schema provided above. "
        "Phrase your message as if you are a college student, typing informally (e.g., using abbreviations, casual language, and minimal punctuation). Do not use overly formal or structured responses and do not use emojis. Make your response detailed enough to persuade other players but do not be overly verbose. Shorter messages are more effective; don't use more than a few sentences and prefer fewer when possible."
    )

    player_discuss_team_evil_side = (
        "Evaluate the proposed mission team consisting of {proposed_team_players}. "
        "Your goal is to ensure at least one evil player is included while maintaining your cover.\n\n"
        "Consider:\n"
        "1. Past involvement and actions of each player\n"
        "2. Contributions in previous missions\n"
        "3. Suspicious or trustworthy behaviors\n"
        "4. The team must consist of {team_player_num} players\n\n"
        "If the team lacks an evil player, you should generally disapprove. "
        "Provide a clear and logical analysis based on game history and observations. "
        "Your response should be detailed enough to provide insight but concise enough to be easily understood. Try to make concrete suggestions and justify them while hiding your identity and role. "
        "Please keep it relatively short as talking too much can be seen as suspicious. Do not say what your specific role or your task is, and do not repeat your instructions verbatim. "
        "Provide the message you want to send to the other players following the schema provided above. "
        "Phrase your message as if you are a college student, typing informally (e.g., using abbreviations, casual language, and minimal punctuation). Do not use overly formal or structured responses and do not use emojis. Make your response detailed enough to persuade other players but do not be overly verbose. Shorter messages are more effective; don't use more than a few sentences and prefer fewer when possible."
    )

    # =====================================================================================================================================================================================================================================

    player_team_vote_good_side = (
        "Vote on the proposed mission team consisting of {current_proposed_team_players}. "
        "Your goal is to ensure no evil or suspicious players are on the team.\n\n"
        "Note that {cur_party_rejects} party proposals have been rejected. If five proposals are rejected consecutively, "
        "the evil side wins. Consider this when voting.\n\n"
        "Consider:\n"
        "1. Past involvement and actions of each player\n"
        "2. Contributions in previous missions\n"
        "3. Any indications of players being on the evil side\n"
        "4. Suspicious or trustworthy behaviors\n"
        "When looking for suspicious behavior, consider whether players are behaving suspiciously or illogically with respect to chat messages or party votes, e.g. always rejecting party votes unless they or another specific player is in it, or making assertions without evidence (especially early in the game such as on Quest 1 where evidence is limited) as these may be signs a player is evil.\n"
        "Also consider whether their beliefs align with your own, or if their beliefs seem contrary to the group consensus as there are more Servants than Minions and could also suggest a player is evil.\n"
        "Unless you have a strong reason to doubt a player, it is not always worth arguing for or against specific players, especially early in the game such as on Quest 1.{team_leader_addendum}\n"
        "Choose either 'approve' or 'disapprove' following the schema provided above."
    )

    player_team_vote_evil_side = (
        "Vote on the proposed mission team consisting of {current_proposed_team_players}. "
        "Your goal is to ensure at least one evil player is included while maintaining your cover.\n\n"
        "Note that {cur_party_rejects} party proposals have been rejected. If five proposals are rejected consecutively, "
        "the evil side wins. Consider this when voting.\n\n"
        "If the team lacks an evil player, you should generally disapprove. However, be strategic - "
        "consecutive rejections could expose the evil team, so sometimes, you may need to approve a team with no evil players to hide your true identity and try again in the next party.\n\n"
        "Choose either 'approve' or 'disapprove' following the schema provided above."
    )

    evil_player_quest_vote = (
        "You are on a mission team and must decide whether to make it succeed or fail. "
        "Your primary objective is to secure victory for the evil side by voting for missions to fail. "
        "Therefore, your default choice should be to fail the mission unless you have a compelling strategic reason to do otherwise.\n\n"
        "Answer using the schema provided above. If you want the quest to succeed choose 'true'. If you want it to fail choose 'false'."
    )

    assassin_prompt = (
        "The good team has won three missions. As the Assassin, this is your final chance for victory. "
        "You must identify which player is Merlin.\n\n"
        "Consider the actions, behaviors, and patterns of all players throughout the game. "
        "Look for signs of players who seemed to have special knowledge about evil team members.\n\n"
        "Respond with your guess of player name."
    )

    good_player_quest_vote = (
        "You are on a mission team and must decide whether to make it succeed or fail. "
        "As a member of the good team, your goal is to ensure mission success by voting for missions to succeed."
        "You should always vote for success as a good player as there is no reason for you to fail a quest.\n\n"
        "Answer using the schema provided above. If you want the quest to succeed choose 'true'. If you want it to fail choose 'false'."
    )

    action_selection_prompt = (
        "It is your turn! You need to choose one of the given actions to take next. Each action has different strategic implications:\n\n"
        "1. 'message': Sending a message is usually a good first action. It allows you to:\n"
        "   - Share your thoughts and observations\n"
        "   - Build trust with other players\n"
        "   - Question suspicious behaviors\n"
        "   - Influence team selections\n"
        "2. 'vote_quest': Only available when you're on a mission team. Your vote determines mission success/failure.\n"
        "3. 'vote_party': Vote to approve/reject a proposed mission team. Remember that 5 consecutive rejections result in evil victory.\n"
        "4. 'start_party_vote': Initiates voting on your previously proposed team.\n"
        "    - This will force all players to vote on your previously proposed team.\n"
        "    - You should allow one round of discussion before forcing a voting (to do so, choose end_turn).\n"
        "5. 'propose_party': Allows you to select players for a mission team.\n"
        "    - If there is currently no proposed team, this should be your first action even before sending a message.\n"
        "    - If the prior discussion round for your previously proposed team didn't go well, consider proposing a new team.\n"
        "6. 'end_turn': Ends your turn and allows other players to act and/or discuss.\n"
        "    - Make sure you proposed a party (if you could) before ending your turn, such that there is something to discuss.\n"
        "    - You should also have sent a message as not doing so might make you look suspicious.\n"
        "Please choose one action based on the current game state and your role's objectives.\n"
        "Your current options are: [{choices}].\n"
        "In this turn, you have already taken the following actions: [{past_actions}].\n"
    )