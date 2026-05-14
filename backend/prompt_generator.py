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
        return f"You are role playing as {player_name}. You always have to answer in english. You have to act as a human. So think like one. Do not act like an AI."

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
                return f"You have to find the human under the names {self.player_names}. It is life important! Who is the human? Only answer with the name!"
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
        return f"{context_dialogue}\n\n{action}" if len(message_history) > 0 else action

    def generate_moderator_system_content(self) -> str:
        return f"{self.get_moderator_prompt()}\n\nYou are the Moderator."
