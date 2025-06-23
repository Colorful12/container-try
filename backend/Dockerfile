FROM python:3.13.4-slim

# タイムゾーンを日本時間に設定
ENV TZ=Asia/Tokyo

# 作業ディレクトリ作成
WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# uvicornを使ってFastAPIアプリを起動
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# --host 0.0.0.0 は、Dockerコンテナ内のホストから外部からアクセスできるようにするためのもの（第一の門） CORS設定は第二の門
