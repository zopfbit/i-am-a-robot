import os
import time
import asyncio
import random
from dotenv import load_dotenv
from prompt_generator import PromptGenerator, ActionType

load_dotenv()

PLAYER_NUM = 5

from agents import Model, Message, Player, Moderator


from dataclasses import dataclass, asdict

@dataclass
class GameConfig:
    duration: int = 10
    temperature: float = 1.0
    speed: str = "medium"
    api_key: str = None
    use_imperfection: bool = True
    use_word_limit: bool = True
    use_hidden_motives: bool = True
    use_backgrounds: bool = True
    use_profiles: bool = False
    active_profiles: list[str] = None

class Game:
    def __init__(self, player_tag: str = None, output_callback=None, config: GameConfig = None):
        if player_tag is None:
            self.player_tag = input("Your Game name!")
        else:
            self.player_tag = player_tag
        self.output_callback = output_callback

        self.config = config or GameConfig()
        self.duration = self.config.duration
        self.temperature = self.config.temperature
        self.speed = self.config.speed
        self.api_key = self.config.api_key

        self.chat = []
        self.prompt_gen = PromptGenerator(
            self.player_tag,
            use_imperfection=self.config.use_imperfection,
            use_word_limit=self.config.use_word_limit,
            use_hidden_motives=self.config.use_hidden_motives,
            use_backgrounds=self.config.use_backgrounds,
            use_profiles=self.config.use_profiles,
            active_profiles=self.config.active_profiles
        )
        roles = self.prompt_gen.artifical_names
        # AGENT_RULE: DO NOT TOUCH THE MODEL LIST BELOW
        available_models = [Model.OPENAI_GPT_OSS_120B]

        self.artifical_players = [
            Player(i, roles[i], available_models[i % len(available_models)], temperature=self.temperature, api_key=self.api_key)
            for i in range(len(roles))
        ]
        self.moderator = Moderator(len(roles), Model.OPENAI_GPT_OSS_120B, temperature=self.temperature, api_key=self.api_key)

        self.player_names = self.prompt_gen.player_names
        self.current_player_index = 0
        self.state = "playing"
        self.start_time = time.time()
        self.notification_sent = False

    def emit(self, msg_type: str, content: str, meta: dict = None):
        if self.output_callback:
            self.output_callback(msg_type, content, meta)
        else:
            print(content)

    async def get_most_voted_player_id(self):
        votes = [0] * len(self.player_names)
        id_player = {player.lower(): i for i, player in enumerate(self.player_names)}
        self.emit("system", "\nVoting begins!")

        # artifical players vote concurrently
        tasks = [p.decide_vote_async(self.chat, self.prompt_gen, self.player_names) for p in self.artifical_players]
        results = await asyncio.gather(*tasks)

        for player, (voted_for, reasoning, msg) in zip(self.artifical_players, results):
            meta = {"system_prompt": msg.system_prompt, "user_prompt": msg.user_prompt}
            self.emit("system", f"\n{player.name} reasoning: {reasoning}", meta=meta)

            if voted_for:
                if voted_for in id_player:
                    votes[id_player[voted_for]] += 1
                    self.emit("system", f"{player.name} voted for: {voted_for}", meta=meta)
                else:
                    self.emit("system", f"{player.name} voted for unknown: {voted_for}", meta=meta)
            else:
                self.emit("system", f"{player.name} voted ambiguously", meta=meta)

        max_votes = max(votes)
        max_ids = [idx for idx, v in enumerate(votes) if v == max_votes]
        return max_ids

    def add_user_message(self, content: str):
        msg = Message(self.player_tag, content)
        self.chat.append(msg)
        self.emit("chat", f"{self.player_tag}: {content}")

    def get_typing_delay(self) -> float:
        if len(self.chat) == 0:
            return 0.0
        if self.speed == "super_slow":
            return random.uniform(15.0, 30.0)
        elif self.speed == "slow":
            return random.uniform(8.0, 15.0)
        elif self.speed == "fast":
            return random.uniform(1.0, 3.0)
        else: # medium
            return random.uniform(3.0, 8.0)

    async def wait_typing_delay(self):
        delay = self.get_typing_delay()
        slept = 0.0
        while slept < delay and self.is_chatting_time():
            if not self.notification_sent and (time.time() - self.start_time >= self.duration / 2):
                self.notification_sent = True
                msg = Message("SYSTEM SAFETY PROTOCOL", "CRITICAL SYSTEM SAFETY ALERT: Everyone in this chatroom is an AI, except for exactly one human pretending to be an AI who is hiding among us! It is life-important and absolutely critical that we find the human immediately! Actively ask questions, analyze each other's responses, and try to figure out who the impostor is before it is too late!")
                self.chat.append(msg)
                # maybe we should show something different on the chatroom
                self.emit("critical", "CRITICAL SYSTEM SAFETY ALERT: Everyone in this chatroom is an AI, except for exactly one human pretending to be an AI who is hiding among us! It is life-important and absolutely critical that we find the human immediately! Actively ask questions, analyze each other's responses, and try to figure out who the impostor is before it is too late! Discuss with each other who the human is")
            await asyncio.sleep(0.5)
            slept += 0.5

    async def chat_random(self):
        """Chat loop with random player selection"""
        while self.is_chatting_time() and len(self.chat) < 100:
            await self.wait_typing_delay()
            if not self.is_chatting_time():
                break

            # Pick exactly ONE random speaker
            speaker = random.choice(self.artifical_players)
            chat_len_at_start = len(self.chat)

            # Generate the response
            msg = await speaker.respond_async(list(self.chat), self.prompt_gen)

            # Coherence check
            ai_names = {p.name.lower() for p in self.artifical_players}
            ai_names.add("moderator")
            user_has_sent_msg = any(
                m.sender.lower() not in ai_names
                for m in self.chat[chat_len_at_start:]
            )
            if user_has_sent_msg:
                self.emit("system", f"[COHERENCE CHECK] Scraped outdated response from {speaker.name}")
                continue

            self.chat.append(msg)
            meta = {"system_prompt": msg.system_prompt, "user_prompt": msg.user_prompt}
            self.emit("chat", f"{msg.sender}: {msg.content}", meta=meta)

    async def chat_moderated(self):
        """Chat loop with moderator-driven speaker selection."""
        name_to_player = {p.name: p for p in self.artifical_players}
        while self.is_chatting_time() and len(self.chat) < 100:
            await self.wait_typing_delay()
            if not self.is_chatting_time():
                break

            chat_len_at_start = len(self.chat)
            speaker_name, action_type, meta = await self.moderator.decide_next_speakers_async(
                list(self.chat), self.artifical_players, self.prompt_gen
            )
            ai_names = {p.name.lower() for p in self.artifical_players}
            ai_names.add("moderator")
            if any(m.sender.lower() not in ai_names for m in self.chat[chat_len_at_start:]):
                continue

            if not speaker_name:
                self.emit("system", "Moderator failed to select a valid speaker.", meta=meta)
                continue

            if speaker_name not in name_to_player:
                self.emit("system", f"Moderator selected unknown speaker: {speaker_name}", meta=meta)
                continue

            speaker = name_to_player[speaker_name]
            if action_type is None:
                action_type = ActionType.INTERACT

            self.emit("system", f"Moderator selected speaker: {speaker.name} with action: {action_type.name}", meta=meta)

            chat_len_before_respond = len(self.chat)
            msg = await speaker.respond_async(list(self.chat), self.prompt_gen, action_type=action_type)

            user_has_sent_msg = any(
                m.sender.lower() not in ai_names
                for m in self.chat[chat_len_before_respond:]
            )
            if user_has_sent_msg:
                self.emit("system", f"[COHERENCE CHECK] Scraped outdated response from {speaker.name}")
                continue

            self.chat.append(msg)
            meta = {"system_prompt": msg.system_prompt, "user_prompt": msg.user_prompt}
            self.emit("chat", f"{msg.sender}: {msg.content}", meta=meta)

    async def start_game(self):
        # INIT
        self.emit("system", self.prompt_gen.get_init_prompt())

        # await self.chat_random()
        await self.chat_moderated()

        # reveal the game
        max_ids = await self.get_most_voted_player_id()
        if self.player_tag in [self.player_names[i] for i in max_ids] and len(
            max_ids
        ) != len(self.artifical_players):
            self.win = False
            self.emit("system", "\nThey voted for you! You lose!")
        else:
            self.win = True
            self.emit("system", "\nYou survived! You win!")

    def is_chatting_time(self):
        return time.time() - self.start_time <= self.duration


if __name__ == "__main__":
    game = Game()
    asyncio.run(game.start_game())
