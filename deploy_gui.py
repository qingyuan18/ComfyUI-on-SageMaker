import gradio as gr
import json
import boto3
import jinja2
from jinja2 import Template
import os
import time
import subprocess
import uuid
import json
import base64
import datetime
import io
import traceback
from PIL import Image
import json
import matplotlib.pyplot as plt
from sagemaker_ssh_helper.wrapper import SSHModelWrapper
from sagemaker import get_execution_role,session
from sagemaker import Model, image_uris, serializers, deserializers
import sagemaker
import tempfile

# 初始化sagemaker
role = get_execution_role()
sage_session = session.Session()
bucket = sage_session.default_bucket()
aws_region = boto3.Session().region_name
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
print(f'account id:{account_id}')
print(f'sagemaker sdk version: {sagemaker.__version__}\nrole:  {role}  \nbucket:  {bucket}')


# 初始化全局变量
models = {"s3_bucket": bucket}
node_urls = []
json_content = ""
temp_file_path = None
deploy_info = ""

# 模型菜单选项
model_types = ["基座模型", "lora模型", "controlnet模型", "clip vision模型", "clip模型", "Flux lora模型（xlab）", "Flux ipadapter模型（xlab)","其他模型"]
model_types_values = ["MODEL_PATH","LORA_MODEL_PATH","CONTROLNET_MODEL_PATH","CLIP_VIT_MODEL_PATH","CLIP_MODEL_PATH","FLUX_LORA_MODEL_PATH","FLUX_IPADAPTER_MODEL_PATH","OTHER_MODEL_PATHS"]

# 机型选项
instance_types = ["ml.g5.2xlarge", "ml.g5.4xlarge","ml.g4dn.2xlarge"]


### gui utility functions
def parse_json(file):
    if file is not None:
        file_path = file.name
        with open(file_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        formatted_content = json.dumps(content, indent=2, ensure_ascii=False)
        return formatted_content
    return ""



def save_json(content):
    global temp_file_path
    try:
        # 解析JSON字符串
        parsed_json = json.loads(content)
        # 创建一个临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
            # 写入格式化的JSON
            json.dump(parsed_json, temp_file, indent=2, ensure_ascii=False)
            temp_file_path = temp_file.name
        gr.Info("JSON 内容已保存")
        return content
    except json.JSONDecodeError:
        gr.Error("无效的 JSON 格式")
        return



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
def deploy_model(instance_type, region, progress=gr.Progress()):
    print("here0====")
    global models, node_urls
    deploy_output = ""
    # 读取 Dockerfile 模板
    with open('docker/dockerfile.template', 'r') as file:
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
    with open('docker/Dockerfile_deploy', 'w') as file:
        file.write(rendered_content)

    #gr.Info("New Dockerfile has been generated.")
    progress(0, desc="New Dockerfile has been generated.")

    ## step1: build docker image
    deploy_output=f"开始build镜像（初次build会下载base image，有一定的时间，请耐心等待)"
    #gr.Info(deploy_output)
    progress(0.2, desc=deploy_output)

    # AWS ECR login
    #os.system("aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin 763104351884.dkr.ecr.us-west-2.amazonaws.com")
    os.system("aws ecr get-login-password --region "+aws_region+" | docker login --username AWS --password-stdin 763104351884.dkr.ecr."+aws_region+".amazonaws.com")
    # Build and push
    os.system("bash ./build_and_push.sh ./docker/Dockerfile_deploy")
    # Create dummy file and tar
    with open('dummy', 'w') as f:
        pass
    os.system("tar czvf model.tar.gz dummy")
    # Set S3 paths
    assets_dir = f's3://{bucket}/stablediffusion/assets/'
    model_data = f's3://{bucket}/stablediffusion/assets/model.tar.gz'
    # Upload to S3
    os.system("aws s3 cp model.tar.gz "+assets_dir)
    # Clean up
    os.remove('dummy')
    os.remove('model.tar.gz')

    ## step2: create sagemaker model config
    env = models
    container=f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com/comfyui-inference:latest"

    model = Model(image_uri=container,
              model_data=model_data,
              role=role,
              env=env,
              #dependencies=[SSHModelWrapper.dependency_dir()]
              )

    deploy_output = f"开始部署模型\n实例类型: {instance_type}\n区域: {region}\n"
    #gr.Info(deploy_output)
    progress(0.4, desc=deploy_output)

    ## step3: start deployment
    endpoint_name = f"comfyui-endpoint-{int(time.time())}"
    try:
        deploy_output = f"正在创建 SageMaker endpoint: {endpoint_name}\n"
        gr.Info(deploy_output)
        model.deploy(initial_instance_count=1,
             instance_type=instance_type,
             endpoint_name=endpoint_name,
             container_startup_health_check_timeout=2600
            )
        deploy_output += f"{endpoint_name}部署成功!\n"
        #gr.Info(deploy_output)
        progress(1, desc=deploy_output)
        print("here2====")
        return
    except Exception as e:
        print("here3====")
        print(e)
        deploy_output += f"部署过程中出现错误: {str(e)}\n"
        gr.Info(deploy_output)
        return





# 运行推理
def run_inference(endpoint_name):
    global temp_file_path
    if temp_file_path is None:
        return gr.Error("请先保存 JSON 内容")

    # step1:提交prompt请求
    prompt_json_file=temp_file_path
    prompt_text=""
    with open(prompt_json_file) as f:
        prompt_text = json.load(f)
    client_id = str(uuid.uuid4())
    payload={
         "client_id":client_id,
         "prompt": prompt_text,
         "inference_type":"text2img",
         "method":"queue_prompt"
    }
    prompt_id = predict(endpoint_name,payload)["prompt_id"]
    gr.Info("任务已提交:"+str(prompt_id))

    # step2: 查询状态
    payload={
     "client_id":client_id,
     "prompt_id":prompt_id,
     "inference_type":"text2img",
     "method":"get_status"
    }
    while True:
        status = predict(endpoint_name,payload)
        gr.Info("任务状态:"+status['status'])
        time.sleep(10)
        if status["status"] == "success":
            break

    # step3:获取结果
    payload={
     "client_id":client_id,
     "prompt_id":prompt_id,
     "inference_type":"text2img",
     "method":"get_images"
    }
    result = predict(endpoint_name,payload)
    gr.Info("结果文件:"+str(result['prediction']))

    # step4: 下载并处理 S3 图片
    s3_client = boto3.client('s3')
    image_list = []
    for s3_url in result['prediction']:
        # 解析 S3 URL
        bucket_name = s3_url.split('/')[2]
        object_key = '/'.join(s3_url.split('/')[3:])
        # 下载图片
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            s3_client.download_fileobj(bucket_name, object_key, temp_file)
            temp_file_path = temp_file.name
        # 打开图片并添加到列表
        image = Image.open(temp_file_path)
        image_list.append(image)
        # 删除临时文件
        os.unlink(temp_file_path)
    return image_list


# 获取 SageMaker endpoints
def get_inservice_sagemaker_endpoints(region):
    sagemaker = boto3.client('sagemaker', region_name=region)
    inservice_endpoints = []
    next_token = None
    while True:
        if next_token:
            response = sagemaker.list_endpoints(NextToken=next_token, StatusEquals='InService')
        else:
            response = sagemaker.list_endpoints(StatusEquals='InService')
        inservice_endpoints.extend([endpoint['EndpointName'] for endpoint in response['Endpoints']])
        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break
    return inservice_endpoints


# 刷新 endpoints 列表
def refresh_endpoints(region):
    endpoints = get_inservice_sagemaker_endpoints(region)
    return gr.update(choices=endpoints)

##### sagemaker utility functions ######
s3_client = boto3.client('s3')
def show_local_image(image_path):
    try:
        # 使用PIL库打开图像
        img = Image.open(image_path)
        # 使用matplotlib显示图像
        plt.figure(figsize=(10, 8))
        plt.imshow(img)
        plt.axis('off')  # 不显示坐标轴
        plt.title('Local Image')
        plt.show()
    except FileNotFoundError:
        print(f"Error: The file '{image_path}' was not found.")
    except IOError:
        print(f"Error: Unable to open the image file '{image_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def get_bucket_and_key(s3uri):
    pos = s3uri.find('/', 5)
    bucket = s3uri[5 : pos]
    key = s3uri[pos + 1 : ]
    return bucket, key


def predict(endpoint_name,payload):
    runtime_client = boto3.client('runtime.sagemaker')
    response = runtime_client.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    print(response)
    result = json.loads(response['Body'].read().decode())
    print(result)
    return result


def show_image(result):
    try:
        for image in result['prediction']:
            bucket, key = get_bucket_and_key(image)
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            bytes = obj['Body'].read()
            image = Image.open(io.BytesIO(bytes))
            #resize image to 50% size
            half = 0.5
            out_image = image.resize([int(half * s) for s in image.size])
            out_image.show()

    except Exception as e:
        print("result is not completed, waiting...")


def show_gifs(result):
    import base64
    from IPython import display
    try:
        predictions = result['prediction']
        s3_file_path = predictions[0]
        print("s3 generated gifs path is {}".format(s3_file_path))
        bucket_name, key = get_bucket_and_key(s3_file_path)
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        local_file_path="./ComfyUI_"+timestamp+".gif"
        s3_client.download_file(bucket_name, key, local_file_path)
        with open(local_file_path, 'rb') as fd:
            b64 = base64.b64encode(fd.read()).decode('ascii')
        return display.HTML(f'<img src="data:image/gif;base64,{b64}" />')
    except Exception as e:
        print(e)
        print("result is not completed, waiting...")


def check_sendpoint_status(endpoint_name,timeout=600):
    client = boto3.client('sagemaker')
    current_time=0
    while current_time<timeout:
        client = boto3.client('sagemaker')
        try:
            response = client.describe_endpoint(
            EndpointName=endpoint_name
            )
            if response['EndpointStatus'] !='InService':
                raise Exception (f'{endpoint_name} not ready , please wait....')
        except Exception as ex:
            print(f'{endpoint_name} not ready , please wait....')
            time.sleep(10)
        else:
            status = response['EndpointStatus']
            print(f'{endpoint_name} is ready, status: {status}')
            break





# 创建 Gradio 界面
with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            model_type = gr.Dropdown(choices=model_types, label="模型类型",value=model_types[4])
            model_path = gr.Textbox(label="模型路径", value="s3://sagemaker-us-west-2-687912291502/models/clip")
            comfy_dir = gr.Textbox(label="ComfyUI 模型目录", visible=False)
            s3_path = gr.Textbox(label="S3 模型路径", visible=False)
            model_info = gr.Textbox(label="模型信息", interactive=False)
            add_model_btn = gr.Button("添加模型")
            clear_models_btn = gr.Button("清除模型")

            node_url = gr.Textbox(label="Node Git URL", value="https://github.com/Acly/comfyui-tooling-nodes.git")
            node_info = gr.Textbox(label="Node URL 信息", interactive=False)
            add_node_btn = gr.Button("添加 Customer Nodes")
            clear_nodes_btn = gr.Button("清除 Nodes")

            instance_type = gr.Dropdown(choices=instance_types, label="机型", value="ml.g5.2xlarge")
            region = gr.Textbox(label="区域", value="us-west-2")
            deploy_btn = gr.Button("部署")
            deploy_progress = gr.Textbox("部署进度")
        with gr.Column():
            endpoint_dropdown = gr.Dropdown(label="推理端点", choices=get_inservice_sagemaker_endpoints(region.value))
            refresh_btn = gr.Button("刷新")
            json_file = gr.File(label="上传 JSON 文件")
            json_text = gr.Code(label="JSON 内容", language="json", lines=20)
            save_btn = gr.Button("保存")
            run_btn = gr.Button("运行")
            image_output = gr.Gallery(label="生成的图像")

        ## listener
        add_node_btn.click(add_node, inputs=node_url, outputs=node_info)
        deploy_btn.click(fn=deploy_model, inputs=[instance_type, region],outputs=deploy_progress)
        model_type.change(update_visibility, inputs=[model_type], outputs=[comfy_dir, s3_path, model_path])
        add_model_btn.click(
            add_model,
            inputs=[model_type, model_path, comfy_dir, s3_path],
            outputs=model_info
        )
        clear_models_btn.click(clear_models, outputs=model_info)
        clear_nodes_btn.click(clear_nodes, outputs=node_info)
        refresh_btn.click(refresh_endpoints, inputs=[region], outputs=[endpoint_dropdown])
        json_file.upload(parse_json, inputs=[json_file], outputs=[json_text])
        save_btn.click(save_json, inputs=[json_text])
        run_btn.click(run_inference, inputs=[endpoint_dropdown], outputs=image_output)
        #demo.load(get_status, outputs=deploy_info_text, every=5)
demo.launch(share=True)
