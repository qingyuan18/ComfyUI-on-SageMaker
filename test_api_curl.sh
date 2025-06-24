#!/bin/bash

# API 测试脚本 - 使用 curl 测试 AIGC Hub API
# 使用方法: ./test_api_curl.sh [服务器地址]
# 例如: ./test_api_curl.sh http://localhost:8000
# 或者: ./test_api_curl.sh http://your-server-ip:8000

# 设置服务器地址
if [ -z "$1" ]; then
    SERVER_URL="http://localhost:8000"
else
    SERVER_URL="$1"
fi

echo "=== AIGC Hub API 测试脚本 ==="
echo "服务器地址: $SERVER_URL"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试函数
test_health() {
    echo -e "${BLUE}1. 测试健康检查接口 /health${NC}"
    echo "请求: GET $SERVER_URL/health"
    echo ""
    
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$SERVER_URL/health")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    echo "响应状态码: $http_code"
    echo "响应内容: $body"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ 健康检查通过${NC}"
    else
        echo -e "${RED}✗ 健康检查失败${NC}"
    fi
    echo ""
}

test_t2i() {
    echo -e "${BLUE}2. 测试文本到图像生成接口 /api/t2i${NC}"
    echo "请求: POST $SERVER_URL/api/t2i"
    echo ""
    
    # 构建请求数据
    json_data='{
        "query_type": "flux_t2i",
        "input_prompt": "a beautiful sunset over mountains with golden light",
        "cfg": 7.5,
        "steps": 20,
        "shift": 2.0
    }'
    
    echo "请求参数:"
    echo "$json_data" | jq . 2>/dev/null || echo "$json_data"
    echo ""
    
    echo "发送请求..."
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        "$SERVER_URL/api/t2i")
    
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    echo "响应状态码: $http_code"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ T2I 接口调用成功${NC}"
        # 检查响应是否包含图像数据
        if echo "$body" | grep -q "base64_imag_str"; then
            echo -e "${GREEN}✓ 响应包含图像数据${NC}"
            # 显示响应状态（不显示完整的base64数据）
            echo "$body" | jq 'del(.base64_imag_str) | . + {"base64_imag_str": "... (base64 data hidden) ..."}' 2>/dev/null || echo "响应: $body"
        else
            echo -e "${YELLOW}⚠ 响应不包含图像数据${NC}"
            echo "响应内容: $body"
        fi
    else
        echo -e "${RED}✗ T2I 接口调用失败${NC}"
        echo "错误响应: $body"
    fi
    echo ""
}

test_image_edit() {
    echo -e "${BLUE}3. 测试图像编辑接口 /api/image_edit${NC}"
    echo "请求: POST $SERVER_URL/api/image_edit"
    echo ""
    
    # 创建一个简单的测试图像的base64编码（1x1像素的白色PNG图像）
    test_image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAFfeTFYmwAAAABJRU5ErkJggg=="
    
    # 构建请求数据
    json_data='{
        "query_type": "flux_kontext",
        "input_prompt": "make this image more colorful and vibrant",
        "input_image1_base64_str": "'$test_image_base64'"
    }'
    
    echo "请求参数:"
    echo '{
        "query_type": "flux_kontext",
        "input_prompt": "make this image more colorful and vibrant",
        "input_image1_base64_str": "... (base64 test image data) ..."
    }' | jq . 2>/dev/null || echo "JSON 数据已准备"
    echo ""
    
    echo "发送请求..."
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        "$SERVER_URL/api/image_edit")
    
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    echo "响应状态码: $http_code"
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ 图像编辑接口调用成功${NC}"
        # 检查响应是否包含图像数据
        if echo "$body" | grep -q "base64_imag_str"; then
            echo -e "${GREEN}✓ 响应包含编辑后的图像数据${NC}"
            # 显示响应状态（不显示完整的base64数据）
            echo "$body" | jq 'del(.base64_imag_str) | . + {"base64_imag_str": "... (base64 data hidden) ..."}' 2>/dev/null || echo "响应: $body"
        else
            echo -e "${YELLOW}⚠ 响应不包含图像数据${NC}"
            echo "响应内容: $body"
        fi
    else
        echo -e "${RED}✗ 图像编辑接口调用失败${NC}"
        echo "错误响应: $body"
    fi
    echo ""
}

# 主测试流程
main() {
    echo "开始测试..."
    echo ""
    
    # 测试健康检查
    test_health
    
    # 测试 T2I 接口
    test_t2i
    
    # 测试图像编辑接口
    test_image_edit
    
    echo -e "${BLUE}=== 测试完成 ===${NC}"
    echo ""
    echo "说明:"
    echo "- 如果看到 ✓ 表示测试通过"
    echo "- 如果看到 ✗ 表示测试失败"
    echo "- 如果看到 ⚠ 表示部分成功但可能有问题"
    echo ""
    echo "注意事项:"
    echo "1. 确保 ComfyUI 服务正在运行"
    echo "2. 确保工作流文件存在: sample_workflows/flux_t2i_workflow.json"
    echo "3. 确保工作流文件存在: sample_workflows/flux_kontext_workflow.json"
    echo "4. 确保所需的模型文件已正确安装"
}

# 检查 curl 是否可用
if ! command -v curl &> /dev/null; then
    echo -e "${RED}错误: curl 命令未找到，请先安装 curl${NC}"
    exit 1
fi

# 运行主函数
main
