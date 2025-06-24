# Gradio部署环境变量配置

## 概述

`aigc_hub_util.py` 现在支持通过环境变量进行配置，适用于gradio部署方案。

## 支持的环境变量

### AWS_REGION_S3
- **描述**: S3操作的AWS区域
- **默认值**: `us-east-1`
- **示例**: `us-west-2`

### SERVER_ADDRESS
- **描述**: ComfyUI服务器地址和端口
- **默认值**: `ec2-35-164-90-149.us-west-2.compute.amazonaws.com:8188`
- **示例**: `your-comfyui-server.amazonaws.com:8188`

### BUCKET
- **描述**: 存储生成内容的S3桶路径
- **默认值**: `s3://sagemaker-us-east-1-687912291502/video/output/`
- **示例**: `s3://your-bucket-name/video/output/`

### RESULT_QR_BUCKET
- **描述**: QR码结果的S3桶名称（不含s3://前缀）
- **默认值**: `sagemaker-us-east-1-687912291502`
- **示例**: `your-bucket-name`

## 使用方法

### 在运行gradio应用前设置环境变量

```bash
# 设置环境变量
export AWS_REGION_S3="us-west-2"
export SERVER_ADDRESS="your-server.amazonaws.com:8188"
export BUCKET="s3://your-bucket/output/"
export RESULT_QR_BUCKET="your-bucket"

# 运行gradio应用
python code/aigc_asset_hub.py