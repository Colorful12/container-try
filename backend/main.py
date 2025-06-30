from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json
import uuid
import random
import logging
import os
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from fastapi import HTTPException
from datetime import datetime
import time
import signal
import sys
import atexit
import psutil
import threading
import gc

# タイムゾーンを日本時間に設定
os.environ['TZ'] = 'Asia/Tokyo'

# グローバル変数
memory_leak_data = []
memory_leak_counter = 0
shutdown_requested = False
monitoring_thread = None

# メモリ監視とクラッシュ検知
def memory_monitor():
    """メモリ使用量を監視し、危険な状態を検知"""
    while not shutdown_requested:
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # メモリ使用量が80%を超えた場合に警告
            if memory_percent > 80:
                logger.warning(
                    "【taki】High memory usage detected",
                    extra={
                        "event_type": "high_memory_usage",
                        "memory_percent": memory_percent,
                        "memory_rss_mb": memory_info.rss / 1024 / 1024,
                        "memory_vms_mb": memory_info.vms / 1024 / 1024,
                        "service": "backend",
                        "timestamp": datetime.now().isoformat(),
                        "severity": "warning"
                    }
                )
            
            # メモリ使用量が95%を超えた場合に緊急ログ
            if memory_percent > 95:
                logger.critical(
                    "【taki】Critical memory usage - application may crash soon",
                    extra={
                        "event_type": "critical_memory_usage",
                        "memory_percent": memory_percent,
                        "memory_rss_mb": memory_info.rss / 1024 / 1024,
                        "memory_vms_mb": memory_info.vms / 1024 / 1024,
                        # "memory_leak_count": len(memory_leak_data),
                        "service": "backend",
                        "timestamp": datetime.now().isoformat(),
                        "severity": "critical"
                    }
                )
                
                # 強制的にガベージコレクションを実行
                gc.collect()
                
                # メモリリークデータを一部クリア（緊急時）
                if len(memory_leak_data) > 100:
                    memory_leak_data.clear()
                    logger.warning(
                        "【taki】Emergency memory cleanup performed",
                        extra={
                            "event_type": "emergency_memory_cleanup",
                            "service": "backend",
                            "timestamp": datetime.now().isoformat(),
                            "severity": "warning"
                        }
                    )
            
            time.sleep(10)  # 10秒ごとに監視
            
        except Exception as e:
            logger.error(
                "【taki】Memory monitoring error",
                extra={
                    "event_type": "memory_monitoring_error",
                    "error": str(e),
                    "service": "backend",
                    "timestamp": datetime.now().isoformat(),
                    "severity": "error"
                }
            )
            time.sleep(30)  # エラー時は30秒待機

# 終了時のログ出力
def log_shutdown(reason: str):
    global shutdown_requested, monitoring_thread
    if not shutdown_requested:
        shutdown_requested = True
        
        # 監視スレッドを停止
        if monitoring_thread and monitoring_thread.is_alive():
            monitoring_thread.join(timeout=5)
        
        logger.critical(
            "【taki】Application shutting down",
            extra={
                "event_type": "app_shutdown",
                "shutdown_reason": reason,
                "service": "backend",
                "memory_leak_count": len(memory_leak_data),
                "active_connections": len(manager.active_connections) if 'manager' in globals() else 0,
                "timestamp": datetime.now().isoformat(),
                "severity": "critical"
            }
        )

# シグナルハンドラー
def signal_handler(signum, frame):
    signal_name = signal.Signals(signum).name
    log_shutdown(f"signal_{signal_name}")
    sys.exit(0)

# シグナルを登録
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# 終了時の処理を登録
atexit.register(lambda: log_shutdown("atexit"))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s JST - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # 標準出力
        logging.FileHandler('/tmp/app.log')  # ファイル出力（Datadog Agentが収集）
    ]
)
logger = logging.getLogger(__name__)

# OTel初期化
def setup_otel():
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "backend"),
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("DD_ENV", "production")
    })


    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
    )
    full_endpoint = f"{otlp_endpoint}/v1/traces"
    otlp_exporter = OTLPSpanExporter(endpoint=full_endpoint)    
    
    logger.info(f"【taki】OTLP exporter configured with endpoint: {full_endpoint}")

    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    logger.info(f"【taki】OTel initialized with endpoint: {otlp_endpoint}")


# OTel初期化を実行
setup_otel()

app = FastAPI(title="Bouncing Cats API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI自動計装 （自動で監視機能を追加する, HTTPリクエストのトレースを自動で行う）
FastAPIInstrumentor.instrument_app(app)

# トレーサーを取得
tracer = trace.get_tracer(__name__)  # トレーサー名をモジュール名に設定

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
        logger.warning(
            "【taki】WebSocket connection disconnected",
            extra={
                "event_type": "websocket_disconnect",
                "total_connections": len(self.active_connections),
                "service": "backend",
                "disconnect_reason": "client_disconnect",
                "timestamp": datetime.now().isoformat(),
                "severity": "warning"
            }
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                # 接続が切れた場合は削除対象に追加
                disconnected_connections.append(connection)
                logger.error(
                    "【taki】Failed to send message to WebSocket - connection will be removed",
                    extra={
                        "event_type": "websocket_connection_failed",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "service": "backend",
                        "timestamp": datetime.now().isoformat(),
                        "severity": "error",
                        "total_connections_before": len(self.active_connections)
                    }
                )
        
        # 切断された接続を一括削除
        for connection in disconnected_connections:
            self.active_connections.remove(connection)
            logger.warning(
                "【taki】WebSocket connection removed due to send failure",
                extra={
                    "event_type": "websocket_connection_removed",
                    "service": "backend",
                    "timestamp": datetime.now().isoformat(),
                    "severity": "warning",
                    "total_connections_after": len(self.active_connections)
                }
            )


manager = ConnectionManager()


@app.get("/")
async def root():
    return {"message": "Bouncing Cats API is running!"}


@app.get("/health")
async def health():
    logger.info("【taki】Health check: OK!")
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    with tracer.start_as_current_span("websocket_connection") as span:
        span.set_attribute("websocket.endpoint", "/ws")
        span.set_attribute("websocket.protocol", "ws")

        await manager.connect(websocket)
        try:
            while True:
                with tracer.start_as_current_span(
                    "websocket_message_processing"
                ) as msg_span:
                    try:
                        data = await websocket.receive_text()
                        message = json.loads(data)

                        msg_span.set_attribute("message.type", message.get("type"))
                        msg_span.set_attribute("message.data", json.dumps(message))

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
                            # 共通の属性を設定
                            cat_operation = "add"
                            cat_x = message.get("x", 100)
                            cat_y = message.get("y", 100)

                            if random.random() > 1.0:
                                # エラーケース用のトレーサー
                                with tracer.start_as_current_span(
                                    "cat_creation_miss"
                                ) as error_span:
                                    error_span.set_attribute("cat.operation", cat_operation)
                                    error_span.set_attribute("cat.position.x", cat_x)
                                    error_span.set_attribute("cat.position.y", cat_y)
                                    error_span.set_attribute("error.intentional", True)
                                    error_span.set_attribute("error.type", "chaos_testing")
                                    
                                    error_message = "Intentional WebSocket 500 error for chaos testing"
                                    error_span.set_attribute("error.message", error_message)
                                    error_span.record_exception(Exception(error_message))
                                    
                                    logger.info(
                                        "【taki】Intentional WebSocket 500 error triggered",
                                        extra={
                                            "event_type": "intentional_websocket_error",
                                            "error_type": "500_error",
                                            "error_message": error_message,
                                            "service": "backend"
                                        }
                                    )
                                    
                                    # error_response = {
                                    #     "type": "ERROR",
                                    #     "error": "Internal Server Error",
                                    #     "message": error_message,
                                    #     "chaos_testing": True
                                    # }
                                    # await websocket.send_text(json.dumps(error_response))
                                    raise HTTPException(
                                        status_code=500,
                                        detail={
                                            "error": "Internal Server Error",
                                            "message": error_message,
                                            "chaos_testing": True
                                        }
                                    )
                            else:
                                with tracer.start_as_current_span(
                                    "cat_creation"
                                ) as success_span:
                                    success_span.set_attribute("cat.operation", cat_operation)
                                    success_span.set_attribute("cat.position.x", cat_x)
                                    success_span.set_attribute("cat.position.y", cat_y)
                                    
                                    cat_data = {
                                        "type": "NEW_CAT",
                                        "id": str(uuid.uuid4()),
                                        "x": cat_x,
                                        "y": cat_y
                                    }

                                    success_span.set_attribute("cat.id", cat_data["id"])
                                    success_span.set_attribute("cat.creation.status", "success")
                                    if random.random() > 0.7:
                                        time.sleep(5)
                                    #global memory_leak_counter
                                    #memory_leak_counter += 1
                                    #leak_data = {
                                    #    "id": f"websocket_memory_hog_{memory_leak_counter}",
                                    #    "data": "cat" * 500000,
                                    #    "timestamp": time.time(),
                                    #    "cat_id": cat_data["id"],
                                    #    "metadata": {
                                    #        "x": cat_x,
                                    #        "y": cat_y,
                                    #        "counter": memory_leak_counter,
                                    #        "source": "websocket"
                                    #    }
                                    #}
                                    #memory_leak_data.append(leak_data)

                                    logger.info(
                                        "【taki】Adding new cat",
                                        extra={
                                            "event_type": "cat_added",
                                            "cat_id": cat_data["id"],
                                            "cat_position": {
                                                "x": cat_data["x"],
                                                "y": cat_data["y"]
                                            },
                                            #"memory_leak_count": len(memory_leak_data),
                                            #"memory_leak_size_mb": len(memory_leak_data) * 0.05,  # 50KB = 0.05MB
                                            "service": "backend"
                                        }
                                    )

                                    with tracer.start_as_current_span(
                                        "broadcast_message"
                                    ) as broadcast_span:
                                        broadcast_span.set_attribute(
                                            "broadcast.recipients",
                                            len(manager.active_connections)
                                        )
                                        await manager.broadcast(json.dumps(cat_data))
                    except json.JSONDecodeError as e:
                        logger.error(
                            "【taki】JSON decode error in WebSocket message",
                            extra={
                                "event_type": "websocket_json_error",
                                "error_type": "json_decode_error",
                                "error_message": str(e),
                                "service": "backend"
                            }
                        )
                    except Exception as e:
                        logger.error(
                            "【taki】WebSocket message processing error",
                            extra={
                                "event_type": "websocket_processing_error",
                                "error_type": "message_processing_error",
                                "error_message": str(e),
                                "service": "backend"
                            }
                        )
        except WebSocketDisconnect:
            span.set_attribute(
                "websocket.disconnect_reason", "client_disconnect"
            )
            manager.disconnect(websocket)
            logger.info(
                "【taki】WebSocket client disconnected",
                extra={
                    "event_type": "websocket_disconnect",
                    "service": "backend"
                }
            )
        except Exception as e:
            span.set_attribute("websocket.error", str(e))
            span.record_exception(e)
            logger.error(
                "【taki】WebSocket error",
                extra={
                    "event_type": "websocket_error",
                    "error": str(e),
                    "service": "backend",
                    "error_type": "websocket_exception",
                    "timestamp": datetime.now().isoformat(),
                    "severity": "error"
                }
            )
            manager.disconnect(websocket)


@app.post("/add-cat")
async def add_cat():
    with tracer.start_as_current_span("rest_add_cat") as span:
        span.set_attribute("api.endpoint", "/add-cat")
        span.set_attribute("api.method", "POST")

        with tracer.start_as_current_span("rest_cat_creation") as success_span:
            x_pos = random.randint(50, 750)
            y_pos = random.randint(50, 550)

            success_span.set_attribute("cat.position.x", x_pos)
            success_span.set_attribute("cat.position.y", y_pos)

            cat_data = {
                "type": "NEW_CAT",
                "id": str(uuid.uuid4()),
                "x": x_pos,
                "y": y_pos
            }

            success_span.set_attribute("cat.id", cat_data["id"])
            success_span.set_attribute("cat.creation.status", "success")

            logger.info(
                "【taki】Adding cat via REST API",
                extra={
                    "event_type": "cat_added_rest",
                    "cat_id": cat_data["id"],
                    "cat_position": {
                        "x": cat_data["x"],
                        "y": cat_data["y"]
                    },
                    "service": "backend"
                }
            )

            with tracer.start_as_current_span(
                "broadcast_message"
            ) as broadcast_span:
                broadcast_span.set_attribute(
                    "broadcast.recipients",
                    len(manager.active_connections)
                )
                await manager.broadcast(json.dumps(cat_data))

            return {"message": "Cat added", "cat": cat_data}


@app.on_event("startup")
async def startup_event():
    global monitoring_thread
    
    # メモリ監視スレッドを開始
    monitoring_thread = threading.Thread(target=memory_monitor, daemon=True)
    monitoring_thread.start()
    
    logger.info(
        "【taki】Backend application started successfully",
        extra={
            "event_type": "app_startup_complete",
            "service": "backend",
            "memory_monitoring": "enabled",
            "timestamp": datetime.now().isoformat()
        }
    )
