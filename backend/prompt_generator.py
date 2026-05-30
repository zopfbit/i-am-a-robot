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
        player_roles: list[str] = ["bob", "alice", "david", "eve"],
        use_imperfection: bool = True,
        use_word_limit: bool = True,
        use_hidden_motives: bool = True,
        use_backgrounds: bool = True,
    ):
        self.player_name = player_name
        self.artifical_names = player_roles
        self.player_names = player_roles + [player_name]
        self.use_word_limit = use_word_limit
        self.prompts = {}
        self.personalities = {}

        file_path = os.path.join(os.path.dirname(__file__), "personalities.txt")
        groups = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            raw_groups = content.split("---")
            for rg in raw_groups:
                traits = []
                for line in rg.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        traits.append(line)
                if traits:
                    groups.append(traits)
        except Exception:
            groups = []

        for role in self.artifical_names:
            selected_traits = []
            if len(groups) > 0:
                g1 = groups[0]
                n1 = random.randint(0, 2)
                selected_traits.extend(random.sample(g1, min(len(g1), n1)))
            if len(groups) > 1:
                g2 = groups[1]
                selected_traits.extend(random.sample(g2, min(len(g2), 1)))
            if len(groups) > 2:
                g3 = groups[2]
                n3 = random.randint(0, 2)
                selected_traits.extend(random.sample(g3, min(len(g3), n3)))

            formatted_traits = []
            for idx, trait in enumerate(selected_traits):
                t = trait.strip()
                if idx > 0 and t and t[0].isupper() and not (len(t) > 1 and t[1].isupper()):
                    t = t[0].lower() + t[1:]
                formatted_traits.append(t)

            if formatted_traits:
                personality_str = f"Your personality is: {', '.join(formatted_traits)}."
            else:
                personality_str = "Your personality is: A normal, everyday person."

            # Group 4: Speech Imperfections
            imperfection_str = ""
            if use_imperfection and len(groups) > 3:
                g4 = groups[3]
                selected_imperfections = random.sample(g4, min(len(g4), 1))
                if selected_imperfections:
                    imp_text = selected_imperfections[0].strip()
                    if imp_text:
                        imp_text = imp_text[0].upper() + imp_text[1:]
                    imperfection_str = f" {imp_text}."

            # Heist elements (Group 5, 6)
            heist_str = ""
            is_heist_active = False

            if use_hidden_motives and len(groups) > 4:
                is_heist_active = True
                motive = random.choice(groups[4])
                heist_str += f"\nYour secret motive (do not state this directly): {motive}."

            if use_backgrounds and len(groups) > 5:
                is_heist_active = True
                bg = random.choice(groups[5])
                heist_str += f"\nYour background (naturally shapes your vocabulary and syntax): {bg}."

            if is_heist_active:
                heist_str += "\nStyle instruction: Apply Ernest Hemingway's 'Iceberg Theory'. Keep your explicit speech minimal and dry. Let the underlying tension, your secret motive, and the high stakes bleed through the subtext of your brief remarks. Never explicitly state your background or motive."

            self.personalities[role] = personality_str + imperfection_str + heist_str


    def get_init_prompt(self) -> str:
        roles_str = ", ".join(self.player_names)
        return (
            f"Narrator: {len(self.player_names)} people are in a chatroom: {roles_str}. "
            f"You are here to chat and discuss freely."
        )

    def get_players(self) -> list[str]:
        return self.player_names

    def get_player_system_prompt(self, player_name: str) -> str:
        prompt = f"You are role playing as {player_name}. You always have to answer in english. You have to act as a human. So think like one. Do not act like an AI. No emojis! No asteriks! Don't use the word vibin!"
        if player_name in self.personalities:
            prompt += f" {self.personalities[player_name]}"

        print(f"\n[SYSTEM PROMPT - {player_name}]\n{prompt}\n")
        return prompt

    def get_player_action_prompt(
        self, player_name: str, action_type: ActionType
    ) -> str:
        # maybe we roll randomly which action_type is chosen?
        prompt = ""
        match action_type:
            case ActionType.ASK_QUESTION:
                prompt = f"Ask a question!"
            case ActionType.ANSWER_AND_ASK:
                prompt = f"talk freely and naturally, while interacting with the other players."
            case ActionType.ANSWER_ONLY:
                prompt = f"Answer a question."
            case ActionType.VOTE:
                other_players = [p for p in self.player_names if p != player_name]
                return f"Remember: Everyone in this chatroom is an AI, except for exactly one human pretending to be an AI whom you are trying to find! You have to find that human among the names {self.player_names}. Go over the dialog again. Silence is an AI avoiding technique from humans. For each other player in {other_players}, write a quick one-sentence evaluation of why they might be the human (pretending to be an AI) or why they are likely a fellow AI player. Do NOT write any evaluation, reasoning, or analysis about yourself ({player_name}), as you already know you are an AI. Only evaluate the other players. Then, reason about who is the most suspicious. Remember that you are {player_name} and you must NOT vote for yourself. Come to a conclusion on who to vote for, and then end your message with ##NAME##, replacing NAME with the name of the player you voted for."
            case ActionType.IGNORE_QUESTION:
                prompt = f"Talk freely and naturally"
            case ActionType.CHANGE_TOPIC:
                prompt = f"Talk freely and naturally"
            case _:
                prompt = ""

        if prompt:
            print("config: ", self.use_word_limit)
            if self.use_word_limit:
                word_limits = [5, 10, 15, 20, 25, 30, 100]
                weights = [0.5, 0.5, 0.25, 0.125, 0.0625, 0.03, 0.00125]
                limit = random.choices(word_limits, weights=weights, k=1)[0]
                prompt += f" Answer in under {limit} words."

            n = random.randint(1, 5)
            sentence_word = "sentence" if n == 1 else "sentences"
            prompt += f" Answer in under {n} {sentence_word}."
        return prompt


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
