# 多阶段构建：编译依赖与运行时分离，减小镜像体积
# 容器内工作目录固定为本项目路径，避免与其它服务的 /app 混淆
# 国内 ECS：apt / pip 默认走阿里云镜像，显著加快首次构建
FROM python:3.12-slim AS builder

ARG APP_HOME=/opt/stamping-costing-platform
ARG APT_MIRROR=mirrors.aliyun.com
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
WORKDIR ${APP_HOME}

RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i \
        -e "s|deb.debian.org|${APT_MIRROR}|g" \
        -e "s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i \
        -e "s|deb.debian.org|${APT_MIRROR}|g" \
        -e "s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends build-essential; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    -i "${PIP_INDEX_URL}" \
    --trusted-host "${PIP_TRUSTED_HOST}" \
    -r requirements.txt

FROM python:3.12-slim

ARG APP_HOME=/opt/stamping-costing-platform
ARG APT_MIRROR=mirrors.aliyun.com
WORKDIR ${APP_HOME}

# tzdata：app.common.timezone 使用 ZoneInfo("Asia/Shanghai")，slim 默认没有时区数据
RUN set -eux; \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i \
        -e "s|deb.debian.org|${APT_MIRROR}|g" \
        -e "s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
      sed -i \
        -e "s|deb.debian.org|${APT_MIRROR}|g" \
        -e "s|security.debian.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl tzdata; \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
LABEL com.stamping-costing.platform="true"
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    APP_ENV=production \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

COPY . .

RUN mkdir -p \
    ${APP_HOME}/data \
    ${APP_HOME}/uploads \
    ${APP_HOME}/uploads/avatars \
    ${APP_HOME}/logs

EXPOSE 8000

# SQLite 场景用单进程；勿在镜像内盲目加 --workers
# --no-access-log：访问日志只留请求中间件（含耗时），不重复打 Uvicorn access log
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
