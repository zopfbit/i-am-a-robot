import os
import time
import asyncio
import random
from dotenv import load_dotenv
from prompt_generator import PromptGenerator

load_dotenv()

PLAYER_NUM = 5

from agents import Model, Message, Player, Moderator


class Game:
    def __init__(self, player_tag: str = None, output_callback=None, duration: int = 10, temperature: float = 1.0):
        if player_tag is None:
            self.player_tag = input("Your Game name!")
        else:
            self.player_tag = player_tag
        self.output_callback = output_callback
        self.duration = duration
        self.temperature = temperature
        self.chat = []
        self.prompt_gen = PromptGenerator(self.player_tag)
        roles = self.prompt_gen.artifical_names
        # AGENT_RULE: DO NOT TOUCH THE MODEL LIST BELOW
        available_models = [Model.OPENAI_GPT_OSS_120B]

        self.artifical_players = [
            Player(i, roles[i], available_models[i % len(available_models)], temperature=self.temperature)
            for i in range(len(roles))
        ]
        self.moderator = Moderator(len(roles), Model.OPENAI_GPT_OSS_120B, temperature=self.temperature)

        self.player_names = self.prompt_gen.player_names
        self.current_player_index = 0
        self.state = "playing"
        self.start_time = time.time()

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

    async def chat_random(self):
        """Chat loop with random player selection"""
        while self.is_chatting_time() and len(self.chat) < 100:
            k = min(random.randint(1, 3), len(self.artifical_players))
            speakers = random.sample(self.artifical_players, k)
            tasks = [p.respond_async(self.chat, self.prompt_gen) for p in speakers]
            responses = await asyncio.gather(*tasks)
            for msg in responses:
                self.chat.append(msg)
                meta = {"system_prompt": msg.system_prompt, "user_prompt": msg.user_prompt}
                self.emit("chat", f"{msg.sender}: {msg.content}", meta=meta)
            await asyncio.sleep(0) # Yield to event loop to flush websocket queue

    async def chat_moderated(self):
        """Chat loop with moderator-driven speaker selection."""
        name_to_player = {p.name: p for p in self.artifical_players}
        while self.is_chatting_time() and len(self.chat) < 100:
            speaker_names, meta = await self.moderator.decide_next_speakers_async(
                self.chat, self.artifical_players
            )
            self.emit("system", f"Moderator selected next speakers: {', '.join(speaker_names)}", meta=meta)
            speakers = [name_to_player[n] for n in speaker_names if n in name_to_player]
            if not speakers:
                continue
            tasks = [p.respond_async(self.chat, self.prompt_gen) for p in speakers]
            responses = await asyncio.gather(*tasks)
            for msg in responses:
                self.chat.append(msg)
                meta = {"system_prompt": msg.system_prompt, "user_prompt": msg.user_prompt}
                self.emit("chat", f"{msg.sender}: {msg.content}", meta=meta)

    async def start_game(self):
        # INIT
        self.emit("system", self.prompt_gen.get_init_prompt())

        await self.chat_random()
        # await self.chat_moderated()

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
