import time
import sys
import asyncio
import random
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from prompt_generator import PromptGenerator
from agents import Model, Message, Player, Moderator

PLAYER_NUM = 5

class Game:
    def __init__(self, player_tag: str):
        self.player_tag = player_tag
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
        self.win = None
        self.voting_records = []

    def get_most_voted_player_id(self):
        votes = [0] * len(self.player_names)
        id_player = {player: i for i, player in enumerate(self.player_names)}
        print("\nVoting begins!")
        self.voting_records = []

        # only artifical players vote
        for i, player in enumerate(self.artifical_players):
            voted_for, reasoning = player.decide_vote(self.chat, self.prompt_gen, self.player_names)
            print(f"\n{player.name} reasoning: {reasoning}")

            if voted_for:
                votes[id_player[voted_for]] += 1
                print(f"{player.name} voted for: {voted_for}")
            else:
                print(f"{player.name} voted ambiguously")

            self.voting_records.append({
                "voter": player.name,
                "voted_for": voted_for,
                "reasoning": reasoning
            })

        max_votes = max(votes)
        max_ids = [idx for idx, v in enumerate(votes) if v == max_votes]
        return max_ids

    async def _type_out_message(self, sender: str, content: str, char_delay: float = 0.015):
        """Prints a message character-by-character to simulate typing."""
        print()
        print(f"{sender}: ", end="", flush=True)
        for char in content:
            print(char, end="", flush=True)
            await asyncio.sleep(char_delay)
        print()
        print()

    async def chat_random(self):
        """Chat loop with random player selection"""
        while self.is_chatting_time() and len(self.chat) < 100 and self.state == "playing":
            speaker = random.choice(self.artifical_players)
            msg = await speaker.respond_async(self.chat, self.prompt_gen)
            if self.state == "playing":
                self.chat.append(msg)
                await self._type_out_message(msg.sender, msg.content)
            await asyncio.sleep(0.5)

    async def chat_moderated(self):
        """Chat loop with moderator-driven speaker selection."""
        name_to_player = {p.name: p for p in self.artifical_players}
        while len(self.chat) < 10 and self.state == "playing":
            speaker_names = await self.moderator.decide_next_speakers_async(
                self.chat, self.artifical_players, self.prompt_gen
            )
            speakers = [name_to_player[n] for n in speaker_names if n in name_to_player]
            if not speakers:
                await asyncio.sleep(0.5)
                continue
            speaker = speakers[0]
            msg = await speaker.respond_async(self.chat, self.prompt_gen)
            if self.state == "playing":
                self.chat.append(msg)
                await self._type_out_message(msg.sender, msg.content)
            await asyncio.sleep(0.5)

    async def console_input_loop(self):
        """Asynchronously reads input from stdin and appends to the chat."""
        session = PromptSession()
        print(f"\n[Console] Game started. Type your message and press Enter at any time.")
        while self.state == "playing":
            try:
                user_input = await session.prompt_async("> ")
                user_input = user_input.strip()
                if user_input:
                    msg = Message(sender=self.player_tag, content=user_input)
                    self.chat.append(msg)
            except (asyncio.CancelledError, KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"Error reading input: {e}")
                await asyncio.sleep(1)

    async def start_game(self, run_cli_input: bool = True):
        # INIT
        print(self.prompt_gen.get_init_prompt())
        self.start_time = time.time()
        self.state = "playing"

        # ensuring background output does not visually overwrite or corrupt the user's active CLI input line
        with patch_stdout():
            input_task = None
            if run_cli_input:
                input_task = asyncio.create_task(self.console_input_loop())

            # await self.chat_random()
            await self.chat_moderated()

            if input_task:
                input_task.cancel()
                try:
                    await input_task
                except asyncio.CancelledError:
                    pass

        self.state = "ended"

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

        self.save_history_to_file()

    def save_history_to_file(self, filename: str = "game_history.txt"):
        """Writes the used models and game chat history to a text file."""
        try:
            used_models = set()
            for player in self.artifical_players:
                used_models.add(player.model.value)
            if self.moderator:
                used_models.add(self.moderator.model.value)

            with open(filename, "w", encoding="utf-8") as f:
                f.write("Used Models:\n")
                for model in sorted(used_models):
                    f.write(f"- {model}\n")
                f.write("\n" + "="*40 + "\n\n")

                f.write("Game Chat History:\n")
                for msg in self.chat:
                    f.write(f"{msg.sender}: {msg.content}\n")

                f.write("\n" + "="*40 + "\n\n")
                f.write("Voting Results:\n")
                for record in self.voting_records:
                    f.write(f"{record['voter']} voted for: {record['voted_for'] or 'ambiguous'}\n")
                    f.write(f"Reasoning: {record['reasoning']}\n\n")
            print(f"\nGame history successfully saved to {filename}")
        except Exception as e:
            print(f"Error saving game history: {e}")

    def is_chatting_time(self):
        return time.time() - self.start_time <= 10
