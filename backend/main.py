from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import uuid
import random
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("Backend application starting up")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket connection established. "
            f"Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket connection disconnected. "
            f"Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                # 接続が切れた場合は削除
                self.active_connections.remove(connection)
                logger.error(f"Failed to send message to WebSocket: {e}")


manager = ConnectionManager()


@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"Received WebSocket message: {message}")
            if message.get("type") == "ADD_CAT":
                cat_data = {
                    "type": "NEW_CAT",
                    "id": str(uuid.uuid4()),
                    "x": message.get("x", 100),
                    "y": message.get("y", 100)
                }
                logger.info(f"Adding new cat: {cat_data}")
                await manager.broadcast(json.dumps(cat_data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.post("/add-cat")
async def add_cat():
    # REST APIでも猫を追加できるように
    cat_data = {
        "type": "NEW_CAT",
        "id": str(uuid.uuid4()),
        "x": random.randint(50, 750),  # ランダムなX座標
        "y": random.randint(50, 550)   # ランダムなY座標
    }
    logger.info(f"Adding cat via REST API: {cat_data}")
    await manager.broadcast(json.dumps(cat_data))
    return {"message": "Cat added", "cat": cat_data}


@app.on_event("startup")
async def startup_event():
    logger.info("Backend application started successfully")
