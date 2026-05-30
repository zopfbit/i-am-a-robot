import asyncio
import glob
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from main import Game, GameConfig
import os

app = FastAPI()

# Mount the static directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/api/profiles")
async def get_profiles():
    profiles_dir = os.path.join(os.path.dirname(__file__), "profiles")
    files = glob.glob(os.path.join(profiles_dir, "*.persona"))
    result = []
    for filepath in files:
        profile_id = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if data:
                    result.append({
                        "id": profile_id,
                        "name": data.get("name", profile_id),
                        "role": data.get("role", ""),
                        "description": data.get("description", "")
                    })
        except Exception:
            result.append({
                "id": profile_id,
                "name": profile_id.capitalize(),
                "role": "",
                "description": ""
            })
    return result

@app.websocket("/ws/{player_name}")
async def websocket_endpoint(
    websocket: WebSocket,
    player_name: str,
    duration: int = 10,
    temperature: float = 1.0,
    speed: str = "medium",
    api_key: str = None,
    use_imperfection: bool = True,
    use_word_limit: bool = True,
    use_hidden_motives: bool = True,
    use_backgrounds: bool = True,
    use_profiles: bool = False,
    active_profiles: str = None
):
    print(f"[DEBUG server.py] WebSocket connected for {player_name}. Query params -> use_word_limit: {use_word_limit}, use_imperfection: {use_imperfection}, use_hidden_motives: {use_hidden_motives}, use_backgrounds: {use_backgrounds}, use_profiles: {use_profiles}, active_profiles: {active_profiles}")
    await websocket.accept()

    message_queue = asyncio.Queue()

    def output_callback(msg_type: str, content: str, meta: dict = None):
        # We can put items in the queue without needing await if we use put_nowait
        message_queue.put_nowait({"type": msg_type, "content": content, "meta": meta or {}})

    active_list = None
    if active_profiles:
        active_list = [p.strip() for p in active_profiles.split(",") if p.strip()]

    config = GameConfig(
        duration=duration,
        temperature=temperature,
        speed=speed,
        api_key=api_key,
        use_imperfection=use_imperfection,
        use_word_limit=use_word_limit,
        use_hidden_motives=use_hidden_motives,
        use_backgrounds=use_backgrounds,
        use_profiles=use_profiles,
        active_profiles=active_list
    )
    game = Game(player_tag=player_name, output_callback=output_callback, config=config)

    # Background task to drain the queue and send via websocket
    async def send_messages():
        try:
            while True:
                msg = await message_queue.get()
                await websocket.send_json(msg)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Error sending message: {e}")

    async def receive_messages():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "chat":
                    msg_text = data.get("content")
                    game.add_user_message(msg_text)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"Error receiving message: {e}")

    sender_task = asyncio.create_task(send_messages())
    receiver_task = asyncio.create_task(receive_messages())

    try:
        # Start the game loop
        await game.start_game()

        # Keep connection open for a bit to ensure all messages are sent
        await asyncio.sleep(2)

    except WebSocketDisconnect:
        print(f"Client {player_name} disconnected")
    except Exception as e:
        print(f"Game error: {e}")
        try:
            await websocket.send_json({"type": "system", "content": f"Server Error: {str(e)}"})
            await asyncio.sleep(1)
        except:
            pass
    finally:
        sender_task.cancel()
        receiver_task.cancel()
        try:
            await websocket.close()
        except:
            pass

# To run the server directly (useful for local testing without uvicorn command line)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
