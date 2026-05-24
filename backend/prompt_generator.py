import os
import random
from enum import Enum


class ActionType(Enum):
    ASK_QUESTION = 0
    ANSWER_AND_ASK = 1
    ANSWER_ONLY = 2
    VOTE = 3
    IGNORE_QUESTION = 4
    CHANGE_TOPIC = 5
    CAVEMAN_ANSWER = 6


class PromptGenerator:
    def __init__(
        self,
        player_name: str = "iamahuman",
        player_roles: list[str] = ["bob", "charlie", "david", "eve"],
    ):
        self.player_name = player_name
        self.artifical_names = player_roles
        self.player_names = player_roles + [player_name]
        self.prompts = {}
        self.personalities = {}

        file_path = os.path.join(os.path.dirname(__file__), "personalities.txt")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                available_personalities = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            available_personalities = [
                "Your personality is: Grumpy, sarcastic, and always annoyed by everyone.",
                "Your personality is: Overly enthusiastic, cheerful, and a bit naive."
            ]

        if not available_personalities:
            available_personalities = ["Your personality is: A normal, everyday person."]

        for role in self.artifical_names:
            self.personalities[role] = random.choice(available_personalities)

    def get_init_prompt(self) -> str:
        roles_str = ", ".join(self.player_names)
        return (
            f"Narrator: {len(self.player_names)} people are in a room: {roles_str}. "
            f"{len(self.player_names)-1} of you are AIs, but one of you is a human hiding among you. "
            f"Your goal is to find out who the human is."
        )

    def get_players(self) -> list[str]:
        return self.player_names

    def get_player_system_prompt(self, player_name: str) -> str:
        prompt = f"You are role playing as {player_name}. You always have to answer in english. You have to act as a human. So think like one. Do not act like an AI. No emojis!"
        if player_name in self.personalities:
            prompt += f" {self.personalities[player_name]}"
            
        print(f"\n[SYSTEM PROMPT - {player_name}]\n{prompt}\n")
        return prompt

    def get_player_action_prompt(
        self, player_name: str, action_type: ActionType
    ) -> str:
        # maybe we roll randomly which action_type is chosen?
        match action_type:
            case ActionType.ASK_QUESTION:
                return f"Ask caveman question!"
            case ActionType.ANSWER_AND_ASK:
                return f"Answer like a caveman and question like a caveman."
            case ActionType.ANSWER_ONLY:
                return f"Answer like a caveman."
            case ActionType.VOTE:
                return f"You have to find the human under the names {self.player_names}. It is life important! Go over the dialog again, and reason about who is suspicious and why. Remember that you are {player_name} and you must NOT vote for yourself. Come to a conclusion on who to vote for, and then end your message with ##NAME##, replacing NAME with the name of the player you voted for."
            case ActionType.IGNORE_QUESTION:
                return f"Talk about caveman stuff. Ignore the question."
            case ActionType.CHANGE_TOPIC:
                return f"Talk about random stuff."
            case _:
                return ""

    def get_moderator_prompt(self) -> str:
        return "Your Goal is to create a fluent interesting, realistic chat discussion. You can choose which AI can answer and when."

    def generate_player_prompt_content(
        self, name: str, player_id: int, action_type: ActionType, message_history: list['Message']
    ) -> str:
        context_dialogue = "Given the dialog below:\n"
        for msg in message_history:
            context_dialogue += f"{msg.sender}: {msg.content}\n"

        context_dialogue += "End of dialog."

        action = self.get_player_action_prompt(name, action_type)
        final_prompt = f"{context_dialogue}\n\n{action}" if len(message_history) > 0 else action
        
        print(f"\n[PROMPT CONTENT - {name} (Action: {action_type.name})]\n{final_prompt}\n")
        return final_prompt

    def generate_moderator_system_content(self) -> str:
        return f"{self.get_moderator_prompt()}\n\nYou are the Moderator."
