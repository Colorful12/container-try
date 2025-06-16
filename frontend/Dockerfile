# Node.js公式イメージを使用
FROM node:22.15.1

WORKDIR /app

# 依存関係をコピー＆インストール
COPY package*.json ./
RUN npm install

# ソースコードコピー
COPY . .

# 開発サーバーを起動
EXPOSE 4200
CMD ["npm", "start", "--", "--host", "0.0.0.0"]
