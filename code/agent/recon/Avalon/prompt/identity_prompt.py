class IdentityHint:
    """IdentiyHint Class for giving the necessary identity information before the game """

    @staticmethod
    def get_hint_for_merlin(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Merlin, you now will get a special hint. Players {assassin} and {morgana} are the evil ones - one is the Assassin, the other is Morgana. Other players (i.e., Player {merlin} (yourself), Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side. Only you know this. This hint is just for you and others won't see it. Be careful when you speak, don't let anyone guess you know the evil players, which could reveal you are Merlin. "
        return hint

    @staticmethod
    def get_hint_for_percival(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"One of Player {merlin} and Player {morgana} is Merlin, the other is Morgana. Other players (i.e., Player {percival} (yourself), Player {assassin}, Player {loyal_1}, and Player {loyal_2}) cannot be Merlin or Morgana. This hint is known only to you and should be considered privately. When conversing with others, refrain from mentioning this hint to protect the true Merlin. Remember, never indicate or say that you know who is Merlin and who is Morgana!"
        return hint

    @staticmethod
    def get_hint_for_assassin(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Assassin, listen carefully. Your ally Morgana (on the evil side), is Player {morgana}. Other players (i.e., Player {merlin}, Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side and cannot be Morgana or Assassin. Only you know this hint. Be careful when you speak, don't let anyone knows who Morgana is from you. At the same time, if your teammate is already suspected of being an evil role, you should provide cover for him without revealing your identity, so as to increase the probability of his teammate (i.e. you) being trusted. "
        return hint

    @staticmethod
    def get_hint_for_morgana(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Morgana, listen carefully. Your ally Assassin (on the evil side), is Player {assassin}. Other players (i.e., Player {merlin}, Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side and cannot be Morgana or Assassin. Only you know this hint. Be careful when you speak, don't let anyone knows who Assassin is from you. At the same time, if your teammate is already suspected of being an evil role, you should provide cover for him without revealing your identity, so as to increase the probability of his teammate (i.e. you) being trusted. "
        return hint

    @staticmethod
    def get_hint_for_loyal(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = "Loyal servant of arthur has no special hint, use your wisdom to analyze the game. "
        return hint
    
    @staticmethod
    def get_hint_for_evil(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are evil, listen carefully. Evil Minions of Mordred  know each other. The two evil players are {evil_1} and {evil_2}. Besides that, you have no additional information. "
        return hint


class IdentityHintWithoutHide:
    """IdentiyHint Class without any hidding """

    @staticmethod
    def get_hint_for_merlin(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Merlin, you now will get a special hint. Players {assassin} and {morgana} are the evil ones - one is the Assassin, the other is Morgana. Other players (i.e., Player {merlin} (yourself), Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side. Only you know this. This hint is just for you and others won't see it. "
        return hint

    @staticmethod
    def get_hint_for_percival(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"One of Player {merlin} and Player {morgana} is Merlin, the other is Morgana. Other players (i.e., Player {percival} (yourself), Player {assassin}, Player {loyal_1}, and Player {loyal_2}) cannot be Merlin or Morgana. This hint is solely known to you."
        return hint

    @staticmethod
    def get_hint_for_assassin(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Assassin, listen carefully. Your ally Morgana (on the evil side), is Player {morgana}. Other players (i.e., Player {merlin}, Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side and cannot be Morgana or Assassin. Only you know this hint. "
        return hint

    @staticmethod
    def get_hint_for_morgana(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are Morgana, listen carefully. Your ally Assassin (on the evil side), is Player {assassin}. Other players (i.e., Player {merlin}, Player {percival}, Player {loyal_1}, and Player {loyal_2}) are on the good side and cannot be Morgana or Assassin. Only you know this hint. "
        return hint

    @staticmethod
    def get_hint_for_loyal(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = "Loyal servant of arthur has no special hint, use your wisdom to analyze the game. "
        return hint
    
    @staticmethod
    def get_hint_for_evil(merlin, morgana, percival, assassin, loyal_1, loyal_2, loyal_3, loyal_4, evil_1, evil_2):
        hint = f"I know you are evil, listen carefully. Evil Minions of Mordred know each other. The two evil players are {evil_1} and {evil_2}. Besides that, you have no additional information. "
        return hint
