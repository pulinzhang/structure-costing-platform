#!/usr/bin/env bash
# 云主机手工发版（可反复执行）：git pull → 重建镜像 → 替换容器
# 数据目录 ./data ./uploads ./logs 始终保留
#   bash deploy.sh
#   bash deploy.sh --skip-pull
#   bash deploy.sh --stop
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SERVICE_NAME="stamping-costing-platform"
SKIP_PULL=0
DO_STOP=0

usage() {
  cat <<'EOF'
用法: bash deploy.sh [选项]

  （无参数）   git pull --ff-only，重建镜像并替换正在运行的容器
  --skip-pull  不拉代码，按当前目录重建并替换容器
  --stop       停止并删除容器（保留 ./data ./uploads ./logs）
  -h, --help   显示本说明

可反复执行：每次发版都会强制重建并换掉旧容器，SQLite / 上传 / 日志目录不动。
首次：clone 后把 .env.production.example 复制为 .env，改 PASSWORD_SALT 与 CORS_ORIGINS。
Nginx 反代到 127.0.0.1:8000。改宿主机端口可在 .env 设 STAMPING_PUBLISH_PORT。
EOF
}

for arg in "$@"; do
  case "$arg" in
    --skip-pull|--no-pull) SKIP_PULL=1 ;;
    --stop) DO_STOP=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "未找到 docker，请先安装 Docker。" >&2
  exit 1
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "未找到 Docker Compose（docker compose 或 docker-compose）。" >&2
    exit 1
  fi
}

remove_container_if_exists() {
  local name="$1"
  if docker ps -a --format '{{.Names}}' | grep -Fxq "$name"; then
    echo "==> 移除容器 ${name}（避免端口占用；数据卷不删）"
    docker rm -f "$name" >/dev/null
  fi
}

if [[ ! -f docker-compose.yml ]]; then
  echo "缺少 docker-compose.yml，请在仓库根目录发版。" >&2
  exit 1
fi

if [[ "$DO_STOP" -eq 1 ]]; then
  echo "==> 停止容器（数据目录保留）"
  compose down --remove-orphans
  remove_container_if_exists "stamping-costing"
  echo "已停止。data / uploads / logs 仍在 $ROOT"
  exit 0
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.production.example ]]; then
    cp .env.production.example .env
    echo "已从 .env.production.example 生成 .env"
    echo "请先编辑 .env：PASSWORD_SALT、CORS_ORIGINS（子域名），再重新执行本脚本。" >&2
    exit 1
  fi
  echo "缺少 .env，且没有 .env.production.example。" >&2
  exit 1
fi

if grep -q 'CHANGE-ME-TO-A-LONG-RANDOM-SECRET' .env; then
  echo "警告: .env 里的 PASSWORD_SALT 仍是占位符，生产请改成随机长字符串。" >&2
fi

mkdir -p data uploads/avatars logs

if [[ "$SKIP_PULL" -eq 0 ]]; then
  if [[ -d .git ]]; then
    echo "==> git pull --ff-only"
    git pull --ff-only
  else
    echo "当前目录不是 git 仓库，跳过 pull。若要用拉代码发版，请先 clone。" >&2
  fi
else
  echo "==> 跳过 git pull"
fi

echo "==> 重建镜像（旧容器继续提供服务，直到下一步替换）"
compose build --pull=false

# 旧版 compose 曾用 container_name=stamping-costing，会占住同一端口
remove_container_if_exists "stamping-costing"

echo "==> 替换容器（保留 data / uploads / logs）"
compose up -d --force-recreate --remove-orphans --no-build

echo "==> 清理本项目旧镜像（不影响其它容器）"
docker image prune -f --filter "label=com.stamping-costing.platform=true" >/dev/null || true

echo "==> 等待健康检查"
ready=0
for _ in $(seq 1 30); do
  if compose exec -T "$SERVICE_NAME" curl -fsS http://127.0.0.1:8000/login >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" -ne 1 ]]; then
  echo "启动超时，最近日志：" >&2
  compose logs --tail=80
  exit 1
fi

echo "==> 容器状态"
compose ps

publish_port=8000
if grep -qE '^STAMPING_PUBLISH_PORT=' .env; then
  publish_port="$(grep -E '^STAMPING_PUBLISH_PORT=' .env | tail -n 1 | cut -d= -f2- | tr -d '[:space:]')"
fi

echo
echo "发版完成（可再次执行本脚本重复发版）。"
echo "本机探测: curl -I http://127.0.0.1:${publish_port}/login"
echo "看日志: docker compose logs -f --tail=100"
