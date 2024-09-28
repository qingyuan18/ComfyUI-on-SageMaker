import gradio as gr
import json
import boto3
import jinja2

# 初始化全局变量
models = {}
node_urls = []
json_content = ""

# 模型菜单选项
model_types = ["基座模型", "lora模型", "controlnet模型", "clip vision模型", "clip模型", "Flux lora模型（xlab）", "Flux ipadapter模型（xlab)"]

# 添加模型
def add_model(model_type, model_path):
    global models
    models[model_type] = model_path
    return gr.update(value=f"当前模型配置：\n{json.dumps(models, indent=2, ensure_ascii=False)}")

# 添加 customer nodes
def add_node(node_url):
    global node_urls
    node_urls.append(node_url)
    return gr.update(value=f"当前 Node URLs：\n{json.dumps(node_urls, indent=2, ensure_ascii=False)}")

# 部署模型
def deploy_model():
    global models, node_urls
    # 这里应该使用 jinja2 模板来生成 Dockerfile
    # 然后触发 build 和 SageMaker 部署操作
    # 以下只是示例代码
    template = jinja2.Template("""
    FROM base_image

    {% for model_type, model_path in models.items() %}
    COPY {{ model_path }} /models/{{ model_type }}/
    {% endfor %}

    {% for url in node_urls %}
    RUN git clone {{ url }} /custom_nodes/
    {% endfor %}
    """)

    dockerfile_content = template.render(models=models, node_urls=node_urls)

    # 这里应该有构建和部署的代码
    print("Dockerfile content:", dockerfile_content)
    return "模型部署已启动"

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
            add_model_btn = gr.Button("添加模型")
            model_info = gr.Textbox(label="模型信息", interactive=False)

            node_url = gr.Textbox(label="Node Git URL", value="https://github.com/example/custom_node.git")
            add_node_btn = gr.Button("添加 Customer Nodes")
            node_info = gr.Textbox(label="Node URL 信息", interactive=False)

            deploy_btn = gr.Button("部署")
            deploy_info = gr.Textbox(label="部署信息", interactive=False)

        with gr.Column():
            json_file = gr.File(label="上传 JSON 文件")
            json_text = gr.Textbox(label="JSON 内容", lines=10)
            edit_btn = gr.Button("编辑")
            save_btn = gr.Button("保存")
            run_btn = gr.Button("运行")
            image_output = gr.Image(label="生成的图像")

    add_model_btn.click(add_model, inputs=[model_type, model_path], outputs=model_info)
    add_node_btn.click(add_node, inputs=node_url, outputs=node_info)
    deploy_btn.click(deploy_model, outputs=deploy_info)

    edit_btn.click(parse_json, inputs=json_file, outputs=json_text)
    save_btn.click(save_json, inputs=json_text, outputs=json_text)
    run_btn.click(run_inference, outputs=image_output)

demo.launch()
