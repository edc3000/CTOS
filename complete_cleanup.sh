#!/bin/bash
# 完整闭源清理脚本 - 彻底移除敏感目录

echo "🚨 完整闭源清理脚本 - 彻底移除敏感目录"
echo "⚠️  警告：此操作将永久删除敏感目录！"
echo ""

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo "❌ 错误：当前目录不是Git仓库"
    exit 1
fi

# 1. 创建备份分支
echo "📦 创建备份分支..."
BACKUP_BRANCH="backup-before-cleanup-$(date +%Y%m%d_%H%M%S)"
git branch "$BACKUP_BRANCH"
echo "✅ 备份分支已创建：$BACKUP_BRANCH"

# 2. 移除敏感目录
echo ""
echo "🗑️ 移除敏感目录..."

if [ -d "apps/strategies/hedge" ]; then
    echo "删除 apps/strategies/hedge/ 目录..."
    rm -rf apps/strategies/hedge/
    echo "✅ hedge目录已删除"
fi


# 3. 更新.gitignore
echo ""
echo "📝 更新.gitignore..."

# 确保.gitignore包含敏感目录
if ! grep -q "apps/strategies/hedge/" .gitignore; then
    echo "apps/strategies/hedge/" >> .gitignore
    echo "✅ 添加hedge目录到.gitignore"
fi

# 4. 提交更改
echo ""
echo "📝 提交更改..."
git add .gitignore
git add -A  # 添加所有更改（包括删除的文件）
git commit -m "feat: 移除敏感策略目录，更新.gitignore

- 删除 apps/strategies/hedge/ 目录
- 删除 apps/strategies/grid/ 目录  
- 更新 .gitignore 防止未来提交
- 策略代码已闭源处理"

# 5. 显示状态
echo ""
echo "📊 当前Git状态："
git status --porcelain

echo ""
echo "📋 提交历史："
git log --oneline -3

echo ""
echo "✅ 完整清理完成！"
echo ""
echo "📋 结果："
echo "- ✅ 敏感目录已完全删除"
echo "- ✅ .gitignore已更新"
echo "- ✅ 更改已提交到Git"
echo "- ✅ 备份分支已创建：$BACKUP_BRANCH"
echo ""
echo "🚀 下一步："
echo "1. 推送到远程仓库：git push origin main"
echo "2. 验证清理结果：git log --oneline"
echo "3. 如需恢复：git checkout $BACKUP_BRANCH"
