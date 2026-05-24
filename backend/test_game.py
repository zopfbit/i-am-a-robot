import asyncio
from main import Game

async def run():
    def callback(t, c, m=None):
        print(f"EMIT: {t} | {c}")
    g = Game('test', callback)
    await g.start_game()

if __name__ == "__main__":
    asyncio.run(run())
