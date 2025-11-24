FROM python:3.11-slim

WORKDIR /app

# 复制requirements文件
COPY backend/requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ .

# 暴露端口
EXPOSE 10000

# 启动应用
CMD ["python", "app.py"]
