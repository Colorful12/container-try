#!/usr/bin/env python3
"""
Jaegerに直接テストトレースを送信するスクリプト（成功例）
"""

import time
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource

def setup_tracing():
    """トレーシング設定"""
    # リソース設定
    resource = Resource.create({"service.name": "test-buildkit"})
    
    # TracerProvider設定
    provider = TracerProvider(resource=resource)
    
    # Jaeger Exporter設定（コンテナ内のJaegerに直接接続）
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",  # コンテナ名で接続
        agent_port=6831,
    )
    
    # BatchSpanProcessor追加
    processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(processor)
    
    # グローバルTracerProvider設定
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)

def send_test_trace():
    """テストトレースを送信"""
    tracer = setup_tracing()
    
    print("🚀 テストトレースを送信中...")
    
    with tracer.start_as_current_span("test-build-operation") as span:
        span.set_attribute("build.type", "docker")
        span.set_attribute("build.stage", "test")
        
        print("  📝 スパン作成: test-build-operation")
        time.sleep(1)
        
        # 子スパンを作成
        with tracer.start_as_current_span("docker-build") as child_span:
            child_span.set_attribute("docker.image", "test-image")
            child_span.set_attribute("docker.tag", "latest")
            
            print("  📝 子スパン作成: docker-build")
            time.sleep(0.5)
            
            # さらに子スパン
            with tracer.start_as_current_span("layer-build") as layer_span:
                layer_span.set_attribute("layer.name", "base")
                layer_span.set_attribute("layer.size", "100MB")
                
                print("  📝 孫スパン作成: layer-build")
                time.sleep(0.3)
    
    print("✅ テストトレース送信完了！")
    print("🌐 Jaeger UI: http://localhost:16686")
    print("🔍 サービス名: test-buildkit")

if __name__ == "__main__":
    send_test_trace() 
