#!/bin/bash

# BuildKit テストビルドスクリプト

echo "🚀 BuildKit + Jaeger テスト開始"

# BuildKit daemonの接続先設定
export BUILDKIT_HOST=tcp://localhost:1234

echo "📋 利用可能なビルダーを確認..."
buildctl --addr tcp://localhost:1234 debug workers

echo "🔨 バックエンドをビルド中..."
buildctl \
  --addr tcp://localhost:1234 \
  build \
  --frontend=dockerfile.v0 \
  --local context=../backend \
  --local dockerfile=../backend \
  --output type=image,name=container-try-backend:test \
  --progress=plain

echo "🔨 フロントエンドをビルド中..."
buildctl \
  --addr tcp://localhost:1234 \
  build \
  --frontend=dockerfile.v0 \
  --local context=../frontend \
  --local dockerfile=../frontend \
  --output type=image,name=container-try-frontend:test \
  --progress=plain

echo "✅ ビルド完了！"
echo "🔍 Jaeger UIで確認してください: http://localhost:16686" 
