import os
import time
import re
import asyncio
from abc import ABC, abstractmethod
from enum import Enum
from openai import OpenAI, AsyncOpenAI
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
    def __init__(self, sender: str, content: str):
        self.sender = sender
        self.content = content
        self.reasoning = ""
        self.evaluation = ""
        self.system_prompt = ""
        self.user_prompt = ""


class Agent(ABC):
    def __init__(
        self,
        id: int,
        name: str,
        model: Model,
        base_url: str = "https://openrouter.ai/api/v1",
        api_key: str = None,
        temperature: float = 1.0,
    ):
        self.id = id
        self.name = name
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.temperature = temperature

    @abstractmethod
    def get_system_content(
        self,
        prompt_gen: PromptGenerator
    ) -> str:
        """Returns the specific system prompt content for this agent type."""
        pass

    def respond(
        self,
        message_history: list["Message"],
        prompt_gen: PromptGenerator,
        action_type: ActionType = ActionType.ANSWER_AND_ASK,
    ) -> "Message":
        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
        )

        system_content = self.get_system_content(prompt_gen)
        prompt = prompt_gen.generate_player_prompt_content(
            self.name, self.id, action_type, message_history
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ]

        try:
            start_time = time.time()
            response = client.chat.completions.create(
                model=self.model.value,
                messages=messages,
                temperature=self.temperature,
            )
            duration = time.time() - start_time
            content = response.choices[0].message.content

            # Log the response time
            with open("response_times.txt", "a") as f:
                f.write(
                    f"Agent: {self.name}, Model: {self.model.name}, Time: {duration:.2f}s\n"
                )

        except Exception as e:
            content = f"Error generating response: {str(e)}"

        msg_obj = Message(self.name, content)
        msg_obj.system_prompt = system_content
        msg_obj.user_prompt = prompt
        return msg_obj

    async def respond_async(
        self,
        message_history: list["Message"],
        prompt_gen: PromptGenerator,
        action_type: ActionType = ActionType.ANSWER_AND_ASK,
    ) -> "Message":
        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        system_content = self.get_system_content(prompt_gen)
        prompt = prompt_gen.generate_player_prompt_content(
            self.name, self.id, action_type, message_history
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]
        try:
            start_time = time.time()
            response = await client.chat.completions.create(
                model=self.model.value,
                messages=messages,
                temperature=self.temperature,
            )
            duration = time.time() - start_time
            content = response.choices[0].message.content
            with open("response_times.txt", "a") as f:
                f.write(
                    f"Agent: {self.name}, Model: {self.model.name}, Time: {duration:.2f}s\n"
                )

            await asyncio.sleep(len(content) * 0.005)
        except Exception as e:
            content = f"Error generating response: {str(e)}"

        msg_obj = Message(self.name, content)
        msg_obj.system_prompt = system_content
        msg_obj.user_prompt = prompt
        return msg_obj

class Player(Agent):
    def __init__(
        self, id: int, name: str = "Amanda", model: Model = Model.OPENAI_GPT_OSS_120B, temperature: float = 1.0
    ):
        super().__init__(id, name, model, temperature=temperature)
        self.role = name
        self.vote = None

    def get_system_content(
        self,
        prompt_gen: PromptGenerator,
    ) -> str:
        return prompt_gen.get_player_system_prompt(self.name)

    def decide_vote(
        self, message_history: list["Message"], prompt_gen: PromptGenerator, player_names: list[str]
    ) -> tuple[str | None, str, "Message"]:
        msg = self.respond(message_history, prompt_gen, action_type=ActionType.VOTE)
        msg.reasoning = msg.content
        suspects = parse_vote(msg.content, player_names=player_names)

        if len(suspects) != 1:
            self.vote = None
            return None, msg.reasoning, msg

        self.vote = suspects[0]
        return self.vote, msg.reasoning, msg

    async def decide_vote_async(
        self, message_history: list["Message"], prompt_gen: PromptGenerator, player_names: list[str]
    ) -> tuple[str | None, str, "Message"]:
        msg = await self.respond_async(message_history, prompt_gen, action_type=ActionType.VOTE)
        msg.reasoning = msg.content
        suspects = parse_vote(msg.content, player_names=player_names)

        if len(suspects) != 1:
            self.vote = None
            return None, msg.reasoning, msg

        self.vote = suspects[0]
        return self.vote, msg.reasoning, msg


class Moderator(Agent):
    def __init__(self, id: int, model: Model = Model.OPENAI_GPT_OSS_120B, temperature: float = 1.0):
        super().__init__(id, "Moderator", model, temperature=temperature)

    def get_system_content(self, prompt_gen: PromptGenerator) -> str:
        if prompt_gen is None:
            raise ValueError("prompt generator not correctly instantiated through moderator!")
        return prompt_gen.generate_moderator_system_content()

    def _build_speaker_prompt(
        self, message_history: list["Message"], players: list["Player"], prompt_gen: PromptGenerator
    ) -> tuple[str, str]:
        """Build system + user prompts for speaker selection."""
        player_list = ", ".join(p.name for p in players)
        chat_log = "\n".join(
            f"{msg.sender}: {msg.content}" for msg in message_history
        ) or "(no messages yet)"
        system = self.get_system_content(prompt_gen)
        user = (
            f"Conversation so far:\n{chat_log}\n\n"
            f"Which player should speak next? Choose exactly 1 from: [{player_list}]. "
            f"Respond with ONLY the name."
        )
        return system, user

    def decide_next_speakers(
        self, message_history: list["Message"], players: list["Player"], prompt_gen: PromptGenerator
    ) -> tuple[list[str], dict]:
        system_prompt, user_prompt = self._build_speaker_prompt(message_history, players, prompt_gen)
        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model.value,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=self.temperature,
        )
        meta = {"system_prompt": system_prompt, "user_prompt": user_prompt}
        return parse_names(response.choices[0].message.content, player_names=[p.name for p in players]), meta

    async def decide_next_speakers_async(
        self, message_history: list["Message"], players: list["Player"], prompt_gen: PromptGenerator
    ) -> tuple[list[str], dict]:
        system_prompt, user_prompt = self._build_speaker_prompt(message_history, players, prompt_gen)
        client = AsyncOpenAI(base_url=self.base_url, api_key=self.api_key)
        response = await client.chat.completions.create(
            model=self.model.value,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=self.temperature,
        )
        meta = {"system_prompt": system_prompt, "user_prompt": user_prompt}
        return parse_names(response.choices[0].message.content, player_names=[p.name for p in players]), meta

def parse_vote(raw_response: str, player_names: list[str]) -> list[str]:
    """Extracts a valid player name from the raw response, expecting it between ## ##"""
    match = re.search(r'##(.*?)##', raw_response)
    if not match:
        # Fallback to standard parse logic if they fail to follow instructions
        return parse_names(raw_response, player_names)

    return parse_names(match.group(1), player_names)

def parse_names(raw_response: str, player_names: list[str]) -> list[str]:
    """Extracts one valid player name from the raw response.
    Model answer can be like "The human is **iamahuman**.".
    """
    text = raw_response.lower()
    valid_names = [p.lower() for p in player_names]

    found_names = []

    for name in valid_names:
        if name in text:
            found_names.append(name)

    return found_names
