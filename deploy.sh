#!/usr/bin/env bash
# 云主机手工发版（可反复执行）：git pull → 重建镜像 → 替换容器 → 跟随日志
# 数据目录 ./data ./uploads ./logs 始终保留
# 启动后不退出，打印容器日志；Ctrl+C 只回到 shell，容器继续跑
#   bash deploy.sh
#   bash deploy.sh --skip-pull
#   bash deploy.sh --no-follow
#   bash deploy.sh --stop
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

SKIP_PULL=0
DO_STOP=0
NO_FOLLOW=0

usage() {
  cat <<'EOF'
用法: bash deploy.sh [选项]

  （无参数）   git pull --ff-only，重建镜像并替换容器，然后跟随日志
  --skip-pull  不拉代码，按当前目录重建并替换容器，然后跟随日志
  --no-follow  同样发版，但健康检查通过后退出（给 GitHub Actions 用）
  --stop       停止并删除容器（保留 ./data ./uploads ./logs）
  -h, --help   显示本说明

启动后脚本停在日志上，便于看完整启动过程。Ctrl+C 退回 shell，容器不停止。

可反复执行：每次发版都会强制重建并换掉旧容器，SQLite / 上传 / 日志目录不动。
首次：clone 后把 .env.production.example 复制为 .env，改 PASSWORD_SALT 与 CORS_ORIGINS。
宿主机映射 :8000。Nginx 在 Docker 内时 proxy_pass 用 172.17.0.1:8000（勿用容器内 127.0.0.1）。
EOF
}

for arg in "$@"; do
  case "$arg" in
    --skip-pull|--no-pull) SKIP_PULL=1 ;;
    --no-follow) NO_FOLLOW=1 ;;
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

echo "==> 容器状态"
compose ps

publish_port=8000
if grep -qE '^STAMPING_PUBLISH_PORT=' .env; then
  publish_port="$(grep -E '^STAMPING_PUBLISH_PORT=' .env | tail -n 1 | cut -d= -f2- | tr -d '[:space:]')"
fi

echo
echo "发版完成。本机探测: curl -fsS http://127.0.0.1:${publish_port}/health"
echo "停止容器: bash deploy.sh --stop"

if [[ "$NO_FOLLOW" -eq 1 ]]; then
  health_url="http://127.0.0.1:${publish_port}/health"
  echo "==> 等待 ${health_url}"
  healthy=0
  for _ in $(seq 1 30); do
    if curl -fsS "$health_url" >/dev/null; then
      healthy=1
      break
    fi
    sleep 2
  done
  if [[ "$healthy" -ne 1 ]]; then
    echo "健康检查失败: ${health_url}" >&2
    compose ps >&2 || true
    compose logs --tail=80 >&2 || true
    exit 1
  fi
  echo "健康检查通过"
  exit 0
fi

echo "==> 跟随容器日志（Ctrl+C 回到 shell，容器继续运行）"

trap 'echo; echo "已停止跟随日志。容器仍在后台。停止: bash deploy.sh --stop"; exit 0' INT
compose logs -f --tail=all
# 容器自己退出时 logs -f 会结束；Ctrl+C 走上面的 trap
echo "日志流已结束。容器状态："
compose ps
