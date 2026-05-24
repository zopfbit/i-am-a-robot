
import asyncio
from dotenv import load_dotenv

from game import Game

load_dotenv()

if __name__ == "__main__":

    player_name = input("Your Game name! ").strip()
    if not player_name:
        player_name = args.name
    game = Game(player_tag=player_name)
    asyncio.run(game.start_game(run_cli_input=True))
