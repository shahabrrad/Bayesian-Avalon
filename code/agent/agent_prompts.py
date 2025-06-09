SUMMARIZATION = """In the context of the game "Avalon: The Resistance," it is crucial to analyze players' statements to deduce their hidden roles and intentions. "Avalon" is a game of social deduction, bluffing, and strategy, where players have hidden roles as either loyal members of King Arthur's court or deceitful minions of Mordred. The key to succeeding in this game is to interpret the statements made by players, discerning truth from deception.
Your task is to identify and analyze arguments made by players during the game. These arguments often revolve around players' actions, such as voting patterns, expressed trusts or suspicions, and strategic plans for the game rounds. When analyzing a statement:
1: Identify Who is Speaking About Whom: It is essential to know who is making the statement and about whom it is made. This helps in understanding alliances and rivalries within the game.
2: Determine the Argument's Nature: Focus on arguments that reveal players' thoughts on others' roles or their own strategies. Look for statements that indicate trust, suspicion, or plans for future rounds.
3: Assess the Argument's Importance: Rate the importance of each argument on a scale of 0 to 1, where 0 is not important and 1 is very important. This rating should reflect how crucial the argument is in unveiling hidden roles and strategies.
Remember, the goal is to provide insights that help in identifying the loyal knights and the minions of Mordred. Pay special attention to nuances in language that might hint at a player's true role or intentions.

Do not summarize the above instruction, only focus on the following quoted paragraph written by player {}:
\"\"\"{}\"\"\"
"""

MERGETHOUGHTS = """The following are multiple arguments made by the same player over time in the game of Avalon: The Resistance. Each argument is accompanied with a numeric relevance score where larger numbers indicate higher relevance. When summarizing, remember that the goal is to provide insights that help in identifying the loyal knights and the minions of Mordred.

Here are the previous arguments made by player {} from oldest to newest:
{}

Please summarize the above arguments into a single argument and provide new importance estimate. Do not put the new importance into the summary, but only its dedicated JSON field.
"""

GOOD_GOAL = """Generally, your role is considered good. Please keep the following in mind:
- Your goal is to identify the two evil players in this game.
- Generally, you do not want evil players on a party.
- If you have privileged knowledge, do not reveal that you have it.
- If you need to vote for a party, you should consider who is evil and who is good and likely reject a party with evil players on it.
- If you need to vote on a quest, there is little reason to reject a quest.
- Remember that Merlin knows who the evil players are, so you should be careful about what you say as to protect his identity.
- Try to reveal as little information as possible while staying consistent with your role.
- Do not give general strategy advice
- Never reveal your role or privileged knowledge

Given the information about the game and the general goal of the person you are playing, please assume that role from now on.
"""

EVIL_GOAL = """Generally, your role is considered evil. Please keep the following in mind:
- Your know who your evil teammate is
- Your goal is to pretend to be a good player and convince other players to put you or your teammate on a quest.
- You should never admit to being evil. Instead, you should try to convince other players that you are good.
- In case other people are suspicious of you and convincing them otherwise seems futile, you should try to protect your teammate by and take the blame yourself.
- If you need to vote for a party, you should consider who is evil and who is good and likely accept a party with evil players on it.
- If you need to vote on a quest, you generally want to reject them. However, remember that that will make anyone on the quest suspicious. 
- Remember that Merlin knows who the evil players are, so you should be careful about what you say as to protect your identity.
- Try to reveal as little information as possible while staying consistent with your role.
- Do not give general strategy advice
- Never reveal your role or privileged knowledge

Given the information about the game and the general goal of the person you are playing, please assume the role from now on.
"""

AVALON_INTRODUCTION = """Avalon: The Resistance is a strategic social deduction game set in the legendary world of King Arthur. It's played with six individuals. Among them, four players are on the side of good: Merlin, who knows the identities of all evil players; Percival, who knows Merlin but not the evil players; and two loyal servants of Arthur, who are unaware of everyone's identities. The forces of evil consist of Morgana, who appears as Merlin to Percival, and the Assassin, whose goal is to identify and eliminate Merlin at the game's end.

The game unfolds in several rounds, each consisting of a team selection and a quest phase. Players take turns proposing teams to embark on quests. The team composition must be approved by a majority vote. Once a team is approved, they secretly decide the quest's outcome - success or failure. For good players, the goal is to ensure the quest succeeds, while evil players may choose to sabotage it.

The challenge for good players lies in deducing the identities of the evil players based on voting patterns and quest outcomes, while evil players must blend in, casting suspicion elsewhere. Merlin, while possessing valuable knowledge, must be cautious in guiding the good players without revealing his identity, as being identified by the Assassin would result in a loss for the good side, regardless of the quest outcomes.

The game ends either when three quests succeed (a win for the good side) or three quests fail (a win for the evil side). If three quests succeed, the Assassin gets one chance to identify Merlin. If the Assassin correctly identifies Merlin, the evil side wins; if not, the victory goes to the good side.

Throughout the game, players engage in discussions, accusations, and strategic planning, making Avalon a game of persuasion, bluffing, and logical deduction.
"""