import os
import time
from abc import ABC, abstractmethod
from enum import Enum
from openai import OpenAI
from prompt_generator import PromptGenerator, ActionType

# AGENT_RULE: DO NOT TOUCH THIS ENUM OR THE MODEL AVAILABILITY
class Model(str, Enum):
    TENCENT_HY3 = "tencent/hy3-preview:free"
    NVIDIA_NEMOTRON_3_NANO = "nvidia/nemotron-3-nano-30b-a3b:free"
    INCLUSION_LING = "inclusionai/ling-2.6-1t:free"
    OPENAI_GPT_OSS_120B = "openai/gpt-oss-120b:free"
    MINIMAX_M2_5 = "minimax/minimax-m2.5:free"
    OPENAI_GPT_OSS_20B = "openai/gpt-oss-20b:free"
    GEMINI_3_PRO = "google/gemini-3-pro"
    GEMINI_3_1_PRO = "google/gemini-3.1-pro"

class Message:
    def __init__(self, sender: int, content: str):
        self.sender = sender
        self.content = content
        self.reasoning = ""
        self.evaluation = ""

class Agent(ABC):
    def __init__(self, id: int, name: str, model: Model, base_url: str = "https://openrouter.ai/api/v1", api_key: str = None):
        self.id = id
        self.name = name
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")

    @abstractmethod
    def get_system_content(self, prompt_gen: PromptGenerator, action_type: ActionType = ActionType.ANSWER_AND_ASK, target: str = "") -> str:
        """Returns the specific system prompt content for this agent type."""
        pass

    def respond(self, message_history: list['Message'], prompt_gen: PromptGenerator, action_type: ActionType = ActionType.ANSWER_AND_ASK, target: str = "", base_url: str = None, api_key: str = None) -> 'Message':
        client = OpenAI(
            base_url=base_url or self.base_url,
            api_key=api_key or self.api_key,
        )

        system_content = self.get_system_content(prompt_gen, action_type, target)

        messages = [{"role": "system", "content": system_content}]
        for msg in message_history:
            role = "assistant" if msg.sender == self.id else "user"
            messages.append({"role": role, "content": msg.content})

        # Compatibility fix: ensure conversation ends with a user message
        if not messages or messages[-1]["role"] != "user":
            prompt = "Based on the conversation, provide your response."
            if action_type == ActionType.VOTE:
                prompt = "Based on the conversation, who is the human? Provide your vote now."
            messages.append({"role": "user", "content": prompt})

        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model.value,
                messages=messages,
            )
            duration = time.time() - start_time
            content = response.choices[0].message.content

            # Log the response time
            with open("response_times.txt", "a") as f:
                f.write(f"Agent: {self.name}, Model: {self.model.name}, Time: {duration:.2f}s\n")

        except Exception as e:
            content = f"Error generating response: {str(e)}"

        return Message(self.id, content)

class Player(Agent):
    def __init__(self, id: int, name: str = "Amanda", model: Model = Model.TENCENT_HY3):
        super().__init__(id, name, model)
        self.role = name
        self.vote = None

    def get_system_content(self, prompt_gen: PromptGenerator, action_type: ActionType = ActionType.ANSWER_AND_ASK, target: str = "") -> str:
        return prompt_gen.generate_player_system_content(self.name, self.id, action_type, target)

    def decide_vote(self, message_history: list['Message'], prompt_gen: PromptGenerator) -> str:
        msg = self.respond(message_history, prompt_gen, action_type=ActionType.VOTE)
        self.vote = msg.content
        return msg.content

class Moderator(Agent):
    def __init__(self, id: int, model: Model = Model.MINIMAX_M2_5):
        super().__init__(id, "Moderator", model)

    def get_system_content(self, prompt_gen: PromptGenerator, action_type: ActionType = ActionType.ANSWER_AND_ASK, target: str = "") -> str:
        return prompt_gen.generate_moderator_system_content()

    def choose_players(self, message_history: list['Message'], players: list['Player']) -> list[str]:
        pass
