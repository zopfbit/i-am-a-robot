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
    def __init__(self):
        self.player_tag = input("Your Game name!")
        self.chat = []
        self.prompt_gen = PromptGenerator(self.player_tag)
        roles = self.prompt_gen.artifical_names
        # AGENT_RULE: DO NOT TOUCH THE MODEL LIST BELOW
        available_models = [Model.OPENAI_GPT_OSS_120B]

        self.artifical_players = [
            Player(i, roles[i], available_models[i % len(available_models)])
            for i in range(len(roles))
        ]
        self.moderator = Moderator(len(roles), Model.OPENAI_GPT_OSS_120B)

        self.player_names = self.prompt_gen.player_names
        self.current_player_index = 0
        self.state = "playing"
        self.start_time = time.time()

    def get_most_voted_player_id(self):
        votes = [0] * len(self.player_names)
        id_player = {player: i for i, player in enumerate(self.player_names)}
        print("\nVoting begins!")

        # only artifical players vote
        for i, player in enumerate(self.artifical_players):
            voted_for, reasoning = player.decide_vote(self.chat, self.prompt_gen, self.player_names)
            print(f"\n{player.name} reasoning: {reasoning}")

            if voted_for:
                votes[id_player[voted_for]] += 1
                print(f"{player.name} voted for: {voted_for}")
            else:
                print(f"{player.name} voted ambiguously")

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
                print(f"{msg.sender}: {msg.content}")

    async def chat_moderated(self):
        """Chat loop with moderator-driven speaker selection."""
        name_to_player = {p.name: p for p in self.artifical_players}
        while self.is_chatting_time() and len(self.chat) < 100:
            speaker_names = await self.moderator.decide_next_speakers_async(
                self.chat, self.artifical_players
            )
            speakers = [name_to_player[n] for n in speaker_names if n in name_to_player]
            if not speakers:
                continue
            tasks = [p.respond_async(self.chat, self.prompt_gen) for p in speakers]
            responses = await asyncio.gather(*tasks)
            for msg in responses:
                self.chat.append(msg)
                print(f"{msg.sender}: {msg.content}")

    async def start_game(self):
        # INIT
        print(self.prompt_gen.get_init_prompt())

        await self.chat_random()
        # await self.chat_moderated()

        # reveal the game
        max_ids = self.get_most_voted_player_id()
        if self.player_tag in [self.player_names[i] for i in max_ids] and len(
            max_ids
        ) != len(self.artifical_players):
            self.win = False
            print("\nThey voted for you! You lose!")
        else:
            self.win = True
            print("\nYou survived! You win!")

    def is_chatting_time(self):
        return time.time() - self.start_time <= 10


game = Game()
asyncio.run(game.start_game())
