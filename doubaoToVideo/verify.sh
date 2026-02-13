#!/bin/bash
echo "=== DoubaoToVideo 插件文件验证 ==="
echo ""

# 检查核心文件
files=(
    "manifest.yaml"
    "provider/doubao_ark.yaml"
    "provider/doubao_ark.py"
    "tools/text_to_video.yaml"
    "tools/text_to_video.py"
    "tools/image_to_video.yaml"
    "tools/image_to_video.py"
    "_assets/icon.svg"
    "requirements.txt"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (缺失)"
        all_exist=false
    fi
done

echo ""
if [ "$all_exist" = true ]; then
    echo "✅ 所有核心文件存在"
    echo ""
    echo "📦 插件大小: $(du -sh . | cut -f1)"
    echo "📦 ZIP包: ../doubaoToVideo.zip ($(ls -lh ../doubaoToVideo.zip | awk '{print $5}'))"
else
    echo "❌ 部分文件缺失，请检查"
fi
