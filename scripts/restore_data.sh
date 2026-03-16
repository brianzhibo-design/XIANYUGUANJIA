#!/bin/bash
# 闲鱼 OpenClaw — 数据恢复脚本（与 backup_data.sh 配对）
# 用法: bash scripts/restore_data.sh <备份目录路径>
# 示例: bash scripts/restore_data.sh data/backups/20250315_020000
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -z "$1" ]; then
  echo "[ERROR] 请指定备份目录路径"
  echo "用法: bash scripts/restore_data.sh <备份目录>"
  echo "示例: bash scripts/restore_data.sh data/backups/20250315_020000"
  echo ""
  echo "可用备份:"
  if [ -d "data/backups" ]; then
    ls -1d data/backups/*/ 2>/dev/null | while read -r d; do
      dir_name=$(basename "$d")
      file_count=$(ls "$d" 2>/dev/null | wc -l | tr -d ' ')
      echo "  $d  ($file_count 个文件)"
    done
  else
    echo "  (未找到备份目录)"
  fi
  exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
  echo "[ERROR] 备份目录不存在: $BACKUP_DIR"
  exit 1
fi

echo "[restore] $(date '+%Y-%m-%d %H:%M:%S') 开始恢复..."
echo "[restore] 备份源: $BACKUP_DIR"
echo ""

echo "[restore] 备份中包含的文件:"
ls -1 "$BACKUP_DIR" | while read -r f; do
  size=$(du -h "$BACKUP_DIR/$f" | cut -f1)
  echo "  $f ($size)"
done
echo ""

read -r -p "[restore] 确认恢复以上文件？已有数据将被覆盖 (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
  echo "[restore] 已取消"
  exit 0
fi

RESTORED=0

mkdir -p data
mkdir -p config

for db_file in "$BACKUP_DIR"/*.db; do
  [ -f "$db_file" ] || continue
  db_name=$(basename "$db_file")
  dest="data/$db_name"

  if [ -f "$dest" ]; then
    cp "$dest" "${dest}.pre-restore.bak"
    echo "[restore]   备份现有 $db_name -> ${db_name}.pre-restore.bak"
  fi

  if command -v sqlite3 &>/dev/null; then
    sqlite3 "$dest" ".restore '$db_file'" 2>/dev/null || cp "$db_file" "$dest"
  else
    cp "$db_file" "$dest"
  fi

  echo "[restore]   ✅ $db_name -> data/"
  RESTORED=$((RESTORED + 1))
done

if [ -f "$BACKUP_DIR/.env" ]; then
  if [ -f ".env" ]; then
    cp ".env" ".env.pre-restore.bak"
    echo "[restore]   备份现有 .env -> .env.pre-restore.bak"
  fi
  cp "$BACKUP_DIR/.env" ".env"
  echo "[restore]   ✅ .env -> 项目根目录"
  RESTORED=$((RESTORED + 1))
fi

if [ -f "$BACKUP_DIR/config.yaml" ]; then
  if [ -f "config/config.yaml" ]; then
    cp "config/config.yaml" "config/config.yaml.pre-restore.bak"
    echo "[restore]   备份现有 config.yaml -> config.yaml.pre-restore.bak"
  fi
  cp "$BACKUP_DIR/config.yaml" "config/config.yaml"
  echo "[restore]   ✅ config.yaml -> config/"
  RESTORED=$((RESTORED + 1))
fi

if [ -f "$BACKUP_DIR/system_config.json" ]; then
  if [ -f "data/system_config.json" ]; then
    cp "data/system_config.json" "data/system_config.json.pre-restore.bak"
  fi
  cp "$BACKUP_DIR/system_config.json" "data/system_config.json"
  echo "[restore]   ✅ system_config.json -> data/"
  RESTORED=$((RESTORED + 1))
fi

echo ""
echo "[restore] 恢复完成: $RESTORED 个文件"
echo "[restore] 原文件已备份为 *.pre-restore.bak (可手动删除)"
echo ""
echo "[restore] 下一步: 运行 bash quick-start.sh 启动服务"
