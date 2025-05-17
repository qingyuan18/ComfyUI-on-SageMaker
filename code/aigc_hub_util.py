from json import JSONDecodeError
import base64
import io
import os
import json
import logging
import time
import re
import json
import magic
import random
import string
from datetime import datetime
import base64
import boto3
from botocore.config import Config
from PIL import Image
from botocore.exceptions import NoCredentialsError
import uuid
import urllib.request
import urllib.parse
from PIL import Image
import io
import numpy as np
import tempfile
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

output_video_path="./generated_videos/"
output_image_path="./generated_images/"

config = Config(
       connect_timeout=1000,
    read_timeout=1000,
)
aws_region_s3 = "us-east-1"
server_address = "ec2-35-164-90-149.us-west-2.compute.amazonaws.com:8188"
BUCKET = "s3://sagemaker-us-east-1-687912291502/video/output/"
RESULT_QR_BUCKET = "sagemaker-us-east-1-687912291502"
session = boto3.session.Session(region_name='us-east-1')
bedrock_runtime = session.client(service_name = 'bedrock-runtime', 
                                 config=config)

#prompt_json_file="./ltxv_image_to_video.json"
prompt_json_file="./wan_image_to_video.json"
prompt_json_file_fill="./flux_fill_image_to_image.json"
prompt_json_file_flux="flux_t2v.json"
WORKING_DIR="generated_videos"

def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            # 读取图像文件
            image_data = image_file.read()
            # 将图像数据转换为Base64编码
            base64_encoded = base64.b64encode(image_data).decode('utf-8')
            return base64_encoded
    except IOError:
        print(f"无法读取文件: {image_path}")
        return None




def queue_prompt(prompt):
    client_id = str(uuid.uuid4())
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    url = "http://"+server_address+"/prompt"
    req = urllib.request.Request(url, data=data)
    #req =  urllib.request.Request("http://ec2-34-222-223-235.us-west-2.compute.amazonaws.com:8188/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen("http://{}/view?{}".format(server_address, url_values)) as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen("http://{}/history/{}".format(server_address, prompt_id)) as response:
        return json.loads(response.read())

    
def get_videos_by_prompt_id(prompt_id):
    output_images={}
    while True:
        try:
            history = get_history(prompt_id)[prompt_id]
            for o in history['outputs']:
                #print("output==",o)
                for node_id in history['outputs']:
                    node_output = history['outputs'][node_id]
                    #print("node_output",node_output)
                    # video branch
                    if 'gifs' in node_output:
                        videos_output = []
                        for video in node_output['gifs']:
                            video_data = get_image(video['filename'], video['subfolder'], video['type'])
                            videos_output.append(video_data)
                        output_images[node_id] = videos_output
            break
        except Exception as e:
            print("waiting to get execution history:",e)
            time.sleep(5)
            continue
    return output_images
    
    
    
    
def get_images_by_prompt_id(prompt_id):
    output_images={}
    while True:
        try:
            history = get_history(prompt_id)[prompt_id]
            for o in history['outputs']:
                #print("output==",o)
                for node_id in history['outputs']:
                    node_output = history['outputs'][node_id]
                    if 'images' in node_output:
                        images_output = []
                        for image in node_output['images']:
                            image_data = get_image(image['filename'], image['subfolder'], image['type'])
                            images_output.append(image_data)
                        output_images[node_id] = images_output
            break
        except Exception as e:
            print("waiting to get execution history:",e)
            time.sleep(5)
            continue
    return output_images


def run_leffa_workflow(main_image,reference_image,user_prompt):   
    global output_image_path
    reference_base64_string = None
    main_base64_string = None
    
    
    if not reference_image:
        reference_base64_string = image_to_base64(reference_image)
    
    if not main_image:
        main_base64_string = image_to_base64(main_image)
    
    workflow_path = "./sample_workflows/模特换装_leffa.json"
    prompt_text=""
    with open(workflow_path) as f:
        prompt_text = json.load(f)
    
    prompt_text['6']['inputs']['text']= user_prompt
    prompt_text['31']['inputs']['seed']=random.randint(0, 99999999998)
    
    prompt_id=queue_prompt(prompt_text)['prompt_id']
    logger.info("prompt_id:"+prompt_id)
    images = get_images_by_prompt_id(prompt_id)
    GIF_LOCATION=None
    for node_id in images:
        logger.info("flux output node id:"+node_id)
        for image_data in images[node_id]:
            GIF_LOCATION = output_image_path+image_path
            logger.info("flux output GIF_LOCATION:"+GIF_LOCATION)
            with open(GIF_LOCATION, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(image_data)
    return GIF_LOCATION




def run_ghibli_workflow(main_image,user_prompt):   
    
    workflow_path = "./sample_workflows/ghibli_flux.json"
    base64_string=""
    base64_string = image_to_base64(main_image)
    
    prompt_text=""
    with open(workflow_path) as f:
        prompt_text = json.load(f)
    
    prompt_text['16']['inputs']['text']= prompt_text
    prompt_text['45']['inputs']['image']=base64_string
    prompt_text['27']['inputs']['seed']=random.randint(0, 99999999998)
    
    prompt_id=queue_prompt(prompt_text)['prompt_id']
    print("prompt_id",prompt_id)
    images = get_images_by_prompt_id(prompt_id)
    GIF_LOCATION=None
    for node_id in images:
        logger.info("flux output node id:"+node_id)
        for image_data in images[node_id]:
            GIF_LOCATION = image_path
            logger.info("flux output GIF_LOCATION:"+GIF_LOCATION)
            with open(GIF_LOCATION, "wb") as binary_file:
                # Write bytes to file
                binary_file.write(image_data)
    return GIF_LOCATION



def upload_to_s3(local_file, bucket, s3_file):
    s3 = boto3.client('s3', region_name=aws_region_s3)
    try:
        s3.upload_file(local_file, bucket, s3_file)
        logger.info(f"Upload Successful: {s3_file}")
        return True
    except FileNotFoundError:
        logger.info("The file was not found")
        return False
    except NoCredentialsError:
        logger.info("Credentials not available")
        return False

def generate_s3_url(bucket, s3_file):
    s3 = boto3.client('s3', region_name=aws_region_s3)
    url = s3.generate_presigned_url('get_object',
                                    Params={'Bucket': bucket, 'Key': s3_file},
                                    ExpiresIn=3600)  # URL有效期为1小时
    return url



class ImageError(Exception):
    "Custom exception for errors returned by Amazon Nova Canvas"

    def __init__(self, message):
        self.message = message



def download_video_from_s3(s3_uri, local_path):
    """
    Download a video file from S3 to local storage
    
    Parameters:
    s3_uri (str): S3 URI in format 's3://bucket-name/path/to/video.mp4'
    local_path (str): Local path where the video will be saved
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Parse S3 URI to get bucket and key
        if not s3_uri.startswith('s3://'):
            raise ValueError("Invalid S3 URI format. Must start with 's3://'")
        
        # Remove 's3://' and split into bucket and key
        path_parts = s3_uri[5:].split('/', 1)
        if len(path_parts) != 2:
            raise ValueError("Invalid S3 URI format")
        
        bucket_name = path_parts[0]
        s3_key = path_parts[1]
        
        # Create directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        fname = timestamp+random_string_name()+'.mp4'
        # Download the file
        logger.info(f"Downloading {s3_uri} to {local_path}/{fname}")
        s3_client.download_file(bucket_name, s3_key, local_path+'/'+fname)
        logger.info("Download completed successfully!")
        
        return f"{local_path}/{fname}"
        
    except Exception as e:
        logger.info(f"Error downloading file: {str(e)}")
        return False

def random_string_name(length=12):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def img_mime(image_path):
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(image_path)
    
    except Exception as e:
        logger.info(f"python-magic detection error: {str(e)}")
        return None

def parse(text: str) -> str:
    pattern = r"<prompt>(.*?)</prompt>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        text = match.group(1)
        return text.strip()
    else:
        return text
        #raise JSONDecodeError




def get_last_frame_base64(video_path):
    return get_last_frame_base64_v3(video_path)


def get_last_frame_base64_v3(video_path):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.info("Error: Could not open video file")
            return None
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 计算最后2秒对应的帧数
        frames_in_1_seconds = int(fps * 1)
        start_frame = max(0, total_frames - frames_in_1_seconds)
        
        frames = []
        # 设置读取位置到最后2秒开始处
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # 读取最后2秒的所有帧
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        
        cap.release()
        
        if not frames:
            logger.info("Error: Could not read any valid frames")
            return None
        
        # 选择最清晰的帧
        best_frame = max(frames, key=lambda f: np.var(cv2.Laplacian(f, cv2.CV_64F)))
        
        # 使用PNG格式进行无损编码
        _, buffer = cv2.imencode('.png', best_frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        
        # 转换为base64编码
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        return base64_image
    except Exception as e:
        logger.info(f"Error: {str(e)}")
        return None
    


    
     


def run_assets_inference(asset_sample_dropdown,image1,image2,text_input1,text_input2):
    if asset_sample_dropdown=="模特换装":
        main_image=image1
        reference_image=image2
        user_prompt=text_input1
        return run_leffa_workflow(main_image,reference_image,mask_image,user_prompt)
    elif asset_sample_dropdown=="吉普力风格转换":
        main_image=image1
        user_prompt=text_input1
        return run_ghibli_workflow(main_image,user_prompt)