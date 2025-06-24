#!/usr/bin/env python3
"""
测试脚本用于验证 aigc_hub_api.py 的功能
"""

import requests
import json
import base64

# API 基础 URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查接口"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health Check Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_t2i_api():
    """测试文本到图像生成接口"""
    payload = {
        "query_type": "flux_t2i",
        "input_prompt": "a beautiful sunset over mountains",
        "cfg": 7.5,
        "steps": 20,
        "shift": 2.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/t2i", json=payload)
        print(f"T2I API Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response status: {result.get('status')}")
            if result.get('base64_imag_str'):
                print("Image generated successfully (base64 data received)")
            else:
                print("No image data in response")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"T2I API test failed: {e}")
        return False

def test_image_edit_api():
    """测试图像编辑接口"""
    # 创建一个简单的测试图像 (1x1 像素的白色图像)
    from PIL import Image
    import io
    
    # 创建测试图像
    img = Image.new('RGB', (100, 100), color='white')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    
    payload = {
        "query_type": "flux_kontext",
        "input_prompt": "make this image more colorful",
        "input_image1_base64_str": img_base64
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/image_edit", json=payload)
        print(f"Image Edit API Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Response status: {result.get('status')}")
            if result.get('base64_imag_str'):
                print("Image edited successfully (base64 data received)")
            else:
                print("No image data in response")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Image Edit API test failed: {e}")
        return False

def main():
    """运行所有测试"""
    print("=== API 测试开始 ===")
    
    # 测试健康检查
    print("\n1. 测试健康检查接口...")
    health_ok = test_health_check()
    
    if not health_ok:
        print("健康检查失败，请确保服务正在运行")
        return
    
    # 测试 T2I 接口
    print("\n2. 测试文本到图像生成接口...")
    t2i_ok = test_t2i_api()
    
    # 测试图像编辑接口
    print("\n3. 测试图像编辑接口...")
    edit_ok = test_image_edit_api()
    
    # 总结
    print("\n=== 测试结果总结 ===")
    print(f"健康检查: {'✓' if health_ok else '✗'}")
    print(f"T2I 接口: {'✓' if t2i_ok else '✗'}")
    print(f"图像编辑接口: {'✓' if edit_ok else '✗'}")

if __name__ == "__main__":
    main()
