from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import uuid
import random
import logging
import os
# タイムゾーンを日本時間に設定
os.environ['TZ'] = 'Asia/Tokyo'

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s JST - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
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

logger.info("【taki】Backend application starting up", extra={
    "event_type": "app_startup",
    "service": "backend"
})


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "【taki】WebSocket connection established",
            extra={
                "event_type": "websocket_connect",
                "total_connections": len(self.active_connections),
                "service": "backend"
            }
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(
            "【taki】WebSocket connection disconnected",
            extra={
                "event_type": "websocket_disconnect",
                "total_connections": len(self.active_connections),
                "service": "backend"
            }
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
                logger.error(
                    "【taki】Failed to send message to WebSocket",
                    extra={
                        "event_type": "websocket_error",
                        "error": str(e),
                        "service": "backend"
                    }
                )


manager = ConnectionManager()


@app.get("/health")
def health_check():
    logger.info("【taki】Health check endpoint called", extra={
        "event_type": "health_check",
        "service": "backend"
    })
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(
                "【taki】Received WebSocket message",
                extra={
                    "event_type": "websocket_message",
                    "message_type": message.get("type"),
                    "message_data": message,
                    "service": "backend"
                }
            )
            if message.get("type") == "ADD_CAT":
                cat_data = {
                    "type": "NEW_CAT",
                    "id": str(uuid.uuid4()),
                    "x": message.get("x", 100),
                    "y": message.get("y", 100)
                }
                logger.info(
                    "【taki】Adding new cat",
                    extra={
                        "event_type": "cat_added",
                        "cat_id": cat_data["id"],
                        "cat_position": {"x": cat_data["x"], "y": cat_data["y"]},
                        "service": "backend"
                    }
                )
                await manager.broadcast(json.dumps(cat_data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("【taki】WebSocket client disconnected", extra={
            "event_type": "websocket_disconnect",
            "service": "backend"
        })
    except Exception as e:
        logger.error(
            "【taki】WebSocket error",
            extra={
                "event_type": "websocket_error",
                "error": str(e),
                "service": "backend"
            }
        )
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
    logger.info(
        "【taki】Adding cat via REST API",
        extra={
            "event_type": "cat_added_rest",
            "cat_id": cat_data["id"],
            "cat_position": {"x": cat_data["x"], "y": cat_data["y"]},
            "service": "backend"
        }
    )
    await manager.broadcast(json.dumps(cat_data))
    return {"message": "Cat added", "cat": cat_data}


@app.on_event("startup")
async def startup_event():
    logger.info("【taki】Backend application started successfully", extra={
        "event_type": "app_startup_complete",
        "service": "backend"
    })
