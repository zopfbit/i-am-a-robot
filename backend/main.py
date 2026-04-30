import os
import time
from dotenv import load_dotenv
from prompt_generator import PromptGenerator

load_dotenv()

PLAYER_NUM=5

from agents import Model, Message, Player, Moderator

class Game():
  def __init__(self):
    self.player_tag = input("Your Game name!")
    self.chat = []
    self.prompt_gen = PromptGenerator(self.player_tag)
    roles = self.prompt_gen.get_players()
    # AGENT_RULE: DO NOT TOUCH THE MODEL LIST BELOW
    available_models = [Model.NVIDIA_NEMOTRON_3_NANO, Model.MINIMAX_M2_5, Model.TENCENT_HY3, Model.OPENAI_GPT_OSS_20B]
    self.players = [Player(i, roles[i], available_models[i % len(available_models)]) for i in range(len(roles))]
    self.current_player_index = 0
    self.state = "playing"
    self.start_time = time.time()

  def parse_vote(self, raw_response: str) -> str:
    """Extracts a valid player name from the raw response without regex."""
    text = raw_response.lower()
    valid_names = [p.name.lower() for p in self.players]

    print(raw_response)

    for name in valid_names:
      if name in text:
        return name
    return None

  def get_most_voted_player_id(self):
    votes = [0] * len(self.players)
    id_player = {player.name: i for i, player in enumerate(self.players)}
    print("\nVoting begins!")
    for i, player in enumerate(self.players):
      print(f"{player.name} is casting their vote...")
      voted_name_raw = player.decide_vote(self.chat, self.prompt_gen)
      voted_for = self.parse_vote(voted_name_raw)

      if voted_for:
          votes[id_player[voted_for]] += 1
          print(f"{player.name} voted for: {voted_for}")
      else:
          print(f"{player.name} voted ambiguously. Raw response: {voted_name_raw}")

    max_votes = max(votes)
    max_ids = [idx for idx, v in enumerate(votes) if v == max_votes]
    return max_ids

  def start_game(self):
    # INIT
    print(self.prompt_gen.get_init_prompt())


    # while self.is_chatting_time():
    #   # do chatting with mod and players
    #   time.sleep(1)

    # reveal the game
    max_ids = self.get_most_voted_player_id()
    if self.player_tag in [self.players[i].name for i in max_ids] and len(max_ids) != len(self.players):
      print("\nThey voted for you! You lose!")
    else:
      print("\nYou survived! You win!")

  def is_chatting_time(self):
    return time.time() - self.start_time <= 10

game = Game()
game.start_game()
