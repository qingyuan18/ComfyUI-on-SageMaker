from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
from aigc_hub_util import *

app = FastAPI(title="ComfyUI Wapper Service")

class QueryRequest(BaseModel):
    query_type: str
    input_prompt: Optional[str] = None
    input_image1_base64_str: Optional[str] = None
    input_image2_base64_str: Optional[str] = None
    cfg: Optional[float] = 7.5
    steps: Optional[int] = 20
    shift: Optional[float] = 2.0
    

class QueryResponse(BaseModel):
    base64_imag_str: str
    status: str
    error: Optional[str] = None

    
    
def run_flux_t2i_workflow(user_prompt, cfg=7.5, steps=20, shift=2.0):

    main_base64_string = ""
    workflow_path = "./sample_workflows/flux_t2i_workflow.json"
    prompt_text=""
    with open(workflow_path) as f:
        prompt_text = json.load(f)

    prompt_text['6']['inputs']['text']= user_prompt
    prompt_text['31']['inputs']['seed']=random.randint(0, 99999999998)

    # 设置可配置参数
    if 'cfg' in prompt_text['31']['inputs']:
        prompt_text['31']['inputs']['cfg'] = cfg
    if 'steps' in prompt_text['31']['inputs']:
        prompt_text['31']['inputs']['steps'] = steps

    # shift 参数可能在其他节点中，需要根据实际工作流结构调整
    # 这里先预留，具体实现需要根据实际的 flux_t2i_workflow.json 文件结构来确定
    # 可能在 FluxGuidance 节点或其他相关节点中
    if shift != 2.0:  # 如果不是默认值，尝试设置
        # 遍历所有节点寻找可能包含 shift 参数的节点
        for node_id, node_data in prompt_text.items():
            if 'inputs' in node_data and 'shift' in node_data['inputs']:
                node_data['inputs']['shift'] = shift
                break

    prompt_id=queue_prompt(prompt_text)['prompt_id']
    logger.info("prompt_id:"+prompt_id)
    images = get_images_by_prompt_id(prompt_id)
    for node_id in images:
        logger.info("flux output node id:"+node_id)
        for image_data in images[node_id]:
            main_base64_string = image_to_base64(image_data)

    return main_base64_string


def run_flux_kontext_workflow(user_prompt, input_image_base64):

    main_base64_string = ""
    workflow_path = "./sample_workflows/flux_kontext_workflow.json"
    prompt_text=""
    with open(workflow_path) as f:
        prompt_text = json.load(f)

    # 设置输入图像到 ETN_LoadImageBase64 节点 (103号节点)
    prompt_text['103']['inputs']['image'] = input_image_base64

    # 设置 FluxKontextCreator 节点 (99号节点) 的参数
    # 根据 flux_kontext_workflow.json 的结构，99号节点使用 inputs 而不是 widgets_values
    prompt_text['99']['inputs']['edit_instruction'] = user_prompt
    prompt_text['99']['inputs']['model'] = "flux-kontext-pro"
    prompt_text['99']['inputs']['seed'] = random.randint(0, 99999999998)


    prompt_id=queue_prompt(prompt_text)['prompt_id']
    logger.info("prompt_id:"+prompt_id)
    images = get_images_by_prompt_id(prompt_id)
    for node_id in images:
        logger.info("flux kontext output node id:"+node_id)
        for image_data in images[node_id]:
            main_base64_string = image_to_base64(image_data)

    return main_base64_string
    

@app.post("/api/t2i")
async def handle_t2i_generation(request: QueryRequest):
    try:
        if request.query_type == "flux_t2i":
            image_base64_str = run_flux_t2i_workflow(
                request.input_prompt,
                cfg=request.cfg,
                steps=request.steps,
                shift=request.shift
            )
            response = QueryResponse(
                base64_imag_str=image_base64_str,
                status="success",
                error=None
            )
            return JSONResponse(content=response.model_dump())
        else:
            raise HTTPException(status_code=400, detail="Invalid query_type")
    except Exception as e:
        response = QueryResponse(
            base64_imag_str="",
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=response.model_dump())
    

@app.post("/api/image_edit")
async def handle_image_edit(request: QueryRequest):
    try:
        if request.query_type == "flux_kontext":
            if not request.input_prompt or not request.input_image1_base64_str:
                raise HTTPException(status_code=400, detail="input_prompt and input_image1_base64_str are required for flux_kontext")

            image_base64_str = run_flux_kontext_workflow(request.input_prompt, request.input_image1_base64_str)
            response = QueryResponse(
                base64_imag_str=image_base64_str,
                status="success",
                error=None
            )
            return JSONResponse(content=response.model_dump())
        else:
            raise HTTPException(status_code=400, detail="Invalid query_type for image_edit endpoint")
    except Exception as e:
        response = QueryResponse(
            base64_imag_str="",
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=response.model_dump())


@app.get("/health")
async def health_check():
    return {"status": "healthy"}