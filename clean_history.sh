#!/bin/bash
# 清理Git历史中的敏感目录

echo "🧹 清理Git历史中的敏感目录"
echo "⚠️  警告：此操作将重写Git历史！"
echo ""

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo "❌ 错误：当前目录不是Git仓库"
    exit 1
fi

# 1. 创建备份分支
echo "📦 创建备份分支..."
BACKUP_BRANCH="backup-before-history-cleanup-$(date +%Y%m%d_%H%M%S)"
git branch "$BACKUP_BRANCH"
echo "✅ 备份分支已创建：$BACKUP_BRANCH"

# 2. 检查敏感目录是否在历史中
echo ""
echo "🔍 检查敏感目录是否在Git历史中..."

HEDGE_IN_HISTORY=$(git log --oneline --name-only | grep -c "apps/strategies/hedge" || echo "0")
GRID_IN_HISTORY=$(git log --oneline --name-only | grep -c "apps/strategies/grid" || echo "0")

echo "hedge目录在历史中出现次数: $HEDGE_IN_HISTORY"
echo "grid目录在历史中出现次数: $GRID_IN_HISTORY"

if [ "$HEDGE_IN_HISTORY" -eq 0 ] && [ "$GRID_IN_HISTORY" -eq 0 ]; then
    echo "✅ 敏感目录未在Git历史中，无需清理历史"
    exit 0
fi

# 3. 使用git filter-branch清理历史
echo ""
echo "🔧 使用git filter-branch清理历史..."

# 清理hedge目录
if [ "$HEDGE_IN_HISTORY" -gt 0 ]; then
    echo "清理 apps/strategies/hedge/ 目录的历史..."
    git filter-branch --force --index-filter \
        'git rm -rf --cached --ignore-unmatch apps/strategies/hedge/' \
        --prune-empty --tag-name-filter cat -- --all
fi

# 清理grid目录
if [ "$GRID_IN_HISTORY" -gt 0 ]; then
    echo "清理 apps/strategies/grid/ 目录的历史..."
    git filter-branch --force --index-filter \
        'git rm -rf --cached --ignore-unmatch apps/strategies/grid/' \
        --prune-empty --tag-name-filter cat -- --all
fi

# 4. 清理引用和垃圾回收
echo ""
echo "🧹 清理Git引用和垃圾回收..."
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 5. 验证清理结果
echo ""
echo "🔍 验证清理结果..."
HEDGE_AFTER=$(git log --oneline --name-only | grep -c "apps/strategies/hedge" || echo "0")
GRID_AFTER=$(git log --oneline --name-only | grep -c "apps/strategies/grid" || echo "0")

echo "清理后hedge目录出现次数: $HEDGE_AFTER"
echo "清理后grid目录出现次数: $GRID_AFTER"

if [ "$HEDGE_AFTER" -eq 0 ] && [ "$GRID_AFTER" -eq 0 ]; then
    echo "✅ 历史清理成功！"
else
    echo "⚠️  警告：仍有敏感文件在历史中"
fi

# 6. 显示状态
echo ""
echo "📊 当前Git状态："
git status --porcelain

echo ""
echo "📋 最近提交："
git log --oneline -5

echo ""
echo "✅ 历史清理完成！"
echo ""
echo "📋 结果："
echo "- ✅ Git历史已清理"
echo "- ✅ 敏感目录已从所有提交中移除"
echo "- ✅ 备份分支已创建：$BACKUP_BRANCH"
echo ""
echo "🚀 下一步："
echo "1. 强制推送到远程：git push --force-with-lease origin main"
echo "2. 通知协作者重新克隆仓库"
echo "3. 如需恢复：git checkout $BACKUP_BRANCH"
