
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml ./
COPY src/ ./src/

# 安装Python依赖
RUN pip install --no-cache-dir -e .

# 创建输出目录
RUN mkdir -p /app/output

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 设置入口点
ENTRYPOINT ["leakage-buster"]

# 默认命令
CMD ["--help"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD leakage-buster --help > /dev/null || exit 1

# 元数据
LABEL maintainer="Leakage Buster Team"
LABEL version="1.0.0"
LABEL description="Data leakage detection and audit tool"
LABEL org.opencontainers.image.source="https://github.com/li147852xu/leakage-buster"
LABEL org.opencontainers.image.licenses="MIT"
