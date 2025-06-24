# Node.js公式イメージを使用
FROM node:22.15.1 AS builder

WORKDIR /app

# npm キャッシュディレクトリを設定
ENV NPM_CONFIG_CACHE=/tmp/npm-cache

# 依存関係をコピー＆インストール（最適化版）
COPY package*.json ./
RUN npm ci --cache /tmp/npm-cache && \
    npm cache clean --force

# ソースコードコピー
COPY . .

# 本番用イメージ
FROM node:22.15.1-slim

WORKDIR /app

# 依存関係のみをコピー
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package*.json ./

# アプリケーションコードをコピー
COPY . .

# 開発サーバーを起動
EXPOSE 4200
CMD ["npm", "start", "--", "--host", "0.0.0.0"]
