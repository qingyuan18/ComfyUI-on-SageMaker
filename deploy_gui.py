import gradio as gr
import json
import boto3
import jinja2
from jinja2 import Template
import os


# 初始化全局变量
models = {}
node_urls = []
json_content = ""

# 模型菜单选项
model_types = ["基座模型", "lora模型", "controlnet模型", "clip vision模型", "clip模型", "Flux lora模型（xlab）", "Flux ipadapter模型（xlab)","其他模型"]

model_types_values = ["MODEL_PATH","LORA_MODEL_PATH","CONTROLNET_MODEL_PATH","CLIP_VIT_MODEL_PATH","CLIP_MODEL_PATH","FLUX_LORA_MODEL_PATH","FLUX_IPADAPTER_MODEL_PATH","OTHER_MODEL_PATHS"]

# 机型选项
instance_types = ["ml.g5.2xlarge", "ml.g5.4xlarge"]

# 清除模型
def clear_models():
    global models
    models = {}
    return gr.update(value="")

# 清除 Nodes
def clear_nodes():
    global node_urls
    node_urls = []
    return gr.update(value="")

def update_visibility(model_type):
    if model_type == "其他模型":
        return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

# 添加模型
def add_model(model_type, model_path, comfy_dir=None, s3_path=None):
    global models
    index = model_types.index(model_type)
    key = model_types_values[index]

    if model_type == "其他模型":
        if comfy_dir and s3_path:
            new_value = f"{comfy_dir}|{s3_path}"
            if key in models:
                models[key] += f";{new_value}"
            else:
                models[key] = new_value
    else:
        models[key] = model_path

    return gr.update(value=f"当前模型配置：\n{json.dumps(models, indent=2, ensure_ascii=False)}")

# 添加 customer nodes
def add_node(node_url):
    global node_urls
    node_urls.append(node_url)
    return gr.update(value=f"当前 Node URLs：\n{json.dumps(node_urls, indent=2, ensure_ascii=False)}")

# 部署模型
def deploy_model():
    global models, node_urls
    # 读取 Dockerfile 模板
    with open('docker/Dockerfile.template', 'r') as file:
        template_content = file.read()
    # 创建 Jinja2 模板对象
    template = Template(template_content)
    # 定义要克隆的 Git 仓库 URL 列表
    git_urls = node_urls
    # 生成 git clone 命令列表
    git_clone_commands = []
    for url in git_urls:
        repo_name = os.path.splitext(os.path.basename(url))[0]
        command = f"RUN git clone {url} /opt/program/custom_nodes/{repo_name}"
        git_clone_commands.append(command)
    # 渲染模板
    rendered_content = template.render(git_clone_commands=git_clone_commands)
    # 将渲染后的内容写入新的 Dockerfile
    with open('Dockerfile_deploy', 'w') as file:
        file.write(rendered_content)

    print("New Dockerfile has been generated.")

    # 构建和部署sagemaker
    ## 初始化部署信息
    deploy_info = f"开始部署模型\n实例类型: {instance_type}\n区域: {region}\n"
    yield deploy_info

    #实际的部署逻辑
    endpoint_name = f"comfyui-endpoint-{int(time.time())}"
    try:
        # 创建 SageMaker endpoint
        # create_sagemaker_endpoint(endpoint_name, instance_type, region, models, node_urls)
        deploy_info += f"正在创建 SageMaker endpoint: {endpoint_name}\n"
        yield deploy_info

        # 模拟部署过程
        for i in range(5):
            time.sleep(2)  # 等待2秒
            deploy_info += f"部署进度: {(i+1)*20}%\n"
            yield deploy_info

        # 使用 AWS CLI 查询部署日志
        cmd = f"aws sagemaker describe-endpoint --endpoint-name {endpoint_name} --region {region}"
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        output, error = process.communicate()

        if process.returncode == 0:
            endpoint_info = json.loads(output)
            status = endpoint_info['EndpointStatus']
            deploy_info += f"Endpoint 状态: {status}\n"
            deploy_info += f"部署日志:\n{json.dumps(endpoint_info, indent=2)}\n"
        else:
            deploy_info += f"获取部署日志失败: {error}\n"

    except Exception as e:
        deploy_info += f"部署过程中出现错误: {str(e)}\n"

    deploy_info += "部署完成\n"
    yield deploy_info


# 解析上传的 JSON 文件
def parse_json(file):
    if file is not None:
        content = file.decode("utf-8")
        return content
    return ""

# 保存 JSON 内容
def save_json(content):
    global json_content
    json_content = content
    return content

# 运行推理
def run_inference():
    global json_content
    # 这里应该调用 SageMaker endpoint
    # 以下只是示例代码
    print("Running inference with:", json_content)
    # 假设返回了一个图像 URL
    return "https://example.com/generated_image.jpg"

# 创建 Gradio 界面
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            model_type = gr.Dropdown(choices=model_types, label="模型类型")
            model_path = gr.Textbox(label="模型路径", value="s3://your_bucket/your_sd_model_path")
            comfy_dir = gr.Textbox(label="ComfyUI 模型目录", visible=False)
            s3_path = gr.Textbox(label="S3 模型路径", visible=False)
            model_info = gr.Textbox(label="模型信息", interactive=False)
            add_model_btn = gr.Button("添加模型")
            clear_models_btn = gr.Button("清除模型")

            node_url = gr.Textbox(label="Node Git URL", value="https://github.com/example/custom_node.git")
            node_info = gr.Textbox(label="Node URL 信息", interactive=False)
            add_node_btn = gr.Button("添加 Customer Nodes")
            clear_nodes_btn = gr.Button("清除 Nodes")


            instance_type = gr.Dropdown(choices=instance_types, label="机型", value="ml.g5.2xlarge")
            region = gr.Textbox(label="区域", value="us-west-2")
            deploy_btn = gr.Button("部署")
            deploy_info = gr.Textbox(label="部署信息", interactive=False)

        with gr.Column():
            json_file = gr.File(label="上传 JSON 文件")
            json_text = gr.Textbox(label="JSON 内容", lines=10)
            edit_btn = gr.Button("编辑")
            save_btn = gr.Button("保存")
            run_btn = gr.Button("运行")
            image_output = gr.Image(label="生成的图像")

    add_node_btn.click(add_node, inputs=node_url, outputs=node_info)
    deploy_btn.click(deploy_model, inputs=[instance_type, region], outputs=deploy_info)
    model_type.change(update_visibility, inputs=[model_type], outputs=[comfy_dir, s3_path, model_path])
    add_model_btn.click(
        add_model,
        inputs=[model_type, model_path, comfy_dir, s3_path],
        outputs=model_info
    )
    clear_models_btn.click(clear_models, outputs=model_info)
    clear_nodes_btn.click(clear_nodes, outputs=node_info)

    edit_btn.click(parse_json, inputs=json_file, outputs=json_text)
    save_btn.click(save_json, inputs=json_text, outputs=json_text)
    run_btn.click(run_inference, outputs=image_output)

demo.launch()