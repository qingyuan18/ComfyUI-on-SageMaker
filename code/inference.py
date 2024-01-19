import websocket
import uuid
import json
import urllib.request
import urllib.parse
import base64
from pydantic import BaseModel, Field
from PIL import Image
import io
import sys
import boto3
import os
import traceback
WORKING_DIR="/tmp"

def get_bucket_and_key(s3uri):
    """
    get_bucket_and_key is helper function
    """
    pos = s3uri.find('/', 5)
    bucket = s3uri[5: pos]
    key = s3uri[pos + 1:]
    return bucket, key

def write_gif_to_s3(images,output_s3uri=""):
    """
    write image to s3 bucket
    """
    s3_client = boto3.client('s3')
    s3_bucket = os.environ.get("s3_bucket", "sagemaker-us-west-2-687912291502")
    prediction = []
    default_output_s3uri = f's3://{s3_bucket}/comfyui_output/images/'
    if output_s3uri is None or output_s3uri=="":
        output_s3uri=default_output_s3uri    
    for node_id in images:
        for image_data in images[node_id]:
            bucket, key = get_bucket_and_key(output_s3uri)
            key = f'{key}{uuid.uuid4()}.jpg'
            GIF_LOCATION = "{}/Comfyui_{}.gif".format(WORKING_DIR, node_id)
            print(GIF_LOCATION)
            key = f'{key}Comfyui_{node_id}.gif'
            with open(GIF_LOCATION, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(image_data)
            s3_client.upload_file(
                Filename=GIF_LOCATION, 
                Bucket=bucket,
                Key=key
            )
            print('image: ', f's3://{bucket}/{key}')
            prediction.append(f's3://{bucket}/{key}')
    return prediction

def write_imgage_to_s3(images,output_s3uri=""):
    """
    write image to s3 bucket
    """
    s3_client = boto3.client('s3')
    s3_bucket = os.environ.get("s3_bucket", "")
    key = "/comfyui_output/images/"
    prediction = []
    default_output_s3uri = f's3://{s3_bucket}/comfyui_output/images/'
    if output_s3uri is None or output_s3uri=="":
        output_s3uri=default_output_s3uri    
    for node_id in images:
        for image_data in images[node_id]:
            image = Image.open(io.BytesIO(image_data))
            bucket, key = get_bucket_and_key(output_s3uri)
            key = f'{key}{uuid.uuid4()}.jpg'
            buf = io.BytesIO()
            image.save(buf, format='JPEG')
            s3_client.put_object(
                Body=buf.getvalue(),
                Bucket=bucket,
                Key=key,
                ContentType='image/jpeg',
                Metadata={
                    "seed": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            print('image: ', f's3://{bucket}/{key}')
            prediction.append(f's3://{bucket}/{key}')
    return prediction

class InferenceOpt(BaseModel):
    prompt_id:str = ""
    client_id:str = ""
    prompt: dict = None
    negative_prompt: str = ""
    steps: int = 20
    inference_type: str = "txt2img"
    method:str = ""

server_address = "127.0.0.1:8188"


def queue_prompt(prompt,client_id):
    #print(prompt)
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    #print(type(data))
    url = "http://"+server_address+"/prompt"
    req = urllib.request.Request(url, data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image_privew(filename):
    url = "http://{}/view?filename={}&type=output".format(server_address,filename)
    with urllib.request.urlopen(url) as response:
        return response.read()

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    #print("here4=="+"http://{}/history/{}".format(server_address, prompt_id))
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

def get_status_old(client_id,prompt_id):
    status="executing"
    ws = websocket.WebSocket()
    ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))
    out = ws.recv()
    if isinstance(out, str):
        message = json.loads(out)
        print("here3===")
        print(message)
        if message['type'] == 'executing':
            data = message['data']
            if data['node'] is None and data['prompt_id'] == prompt_id:
                status = "success"
    return status
    ws.close()


def get_status(prompt_id):
    status="executing"
    out = None
    try:
        with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
             out=json.loads(response.read())
             print("here3==")
             print(out)
        status= out[prompt_id]["status"]["status_str"]
    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        print(f"=================Exception=================\n{ex}")
    return status

    
def get_images(prompt_id):
    output_images={}
    history = get_history(prompt_id)[prompt_id]
    for o in history['outputs']:
        for node_id in history['outputs']:
            node_output = history['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    #image_data = get_image_privew(image['filename'])
                    print("image data==\n")
                    #image_text = (image_data).decode('utf-8') 
                    #print(image_data)
                    images_output.append(image_data)
                output_images[node_id] = images_output
            # video branch
            if 'gifs' in node_output:
                videos_output = []
                for video in node_output['gifs']:
                    video_data = get_image(video['filename'], video['subfolder'], video['type'])
                    videos_output.append(video_data)
                output_images[node_id] = videos_output
    return output_images

def predict_fn(opt:InferenceOpt):
    prediction=[]
    prompt_id = opt.prompt_id
    status = ""
    prompt = opt.prompt
    client_id = opt.client_id
    try:
        if opt.method == "queue_prompt":
            prompt_id = queue_prompt(prompt,client_id)['prompt_id']
            return prompt_id
        if opt.method == "get_status":
            status = get_status(opt.client_id,opt.prompt_id)
            return status
        if opt.method == "get_images":
            output_images=get_images(opt.prompt_id)
            if opt.inference_type == "text2img":
                prediction=write_imgage_to_s3(output_images)
            elif opt.inference_type == "text2vid":
                prediction=write_gif_to_s3(output_images)
    except Exception as ex:
        traceback.print_exc(file=sys.stdout)
        print(f"=================Exception=================\n{ex}")
    print('prediction: ', prediction)
    return prediction