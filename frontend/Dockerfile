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

# 本番用ビルド
RUN npm run build

# Nginxで静的ファイルを配信
FROM nginx:alpine

# ビルドされたファイルをコピー
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# Nginx設定
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 4200
CMD ["nginx", "-g", "daemon off;"]
