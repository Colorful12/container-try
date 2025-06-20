from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import uuid
import random

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # 接続が切れた場合は削除
                self.active_connections.remove(connection)


manager = ConnectionManager()


@app.get("/health")
def health_check():
    return {"status": "ok??"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ADD_CAT":
                # 新しい猫を生成して全クライアントに通知
                cat_data = {
                    "type": "NEW_CAT",
                    "id": str(uuid.uuid4()),
                    "x": message.get("x", 100),
                    "y": message.get("y", 100)
                }
                await manager.broadcast(json.dumps(cat_data))
    except WebSocketDisconnect:
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
    await manager.broadcast(json.dumps(cat_data))
    return {"message": "Cat added", "cat": cat_data}
