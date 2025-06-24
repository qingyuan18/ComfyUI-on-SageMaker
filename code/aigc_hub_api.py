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
    

class QueryResponse(BaseModel):
    base64_imag_str: str
    status: str
    error: Optional[str] = None

    
    
def run_flux_t2i_workflow(user_prompt):   

    main_base64_string = ""
    workflow_path = "./sample_workflows/flux_t2i_workflow.json"
    prompt_text=""
    with open(workflow_path) as f:
        prompt_text = json.load(f)
    
    prompt_text['6']['inputs']['text']= user_prompt
    prompt_text['31']['inputs']['seed']=random.randint(0, 99999999998)
    
    prompt_id=queue_prompt(prompt_text)['prompt_id']
    logger.info("prompt_id:"+prompt_id)
    images = get_images_by_prompt_id(prompt_id)
    for node_id in images:
        logger.info("flux output node id:"+node_id)
        for image_data in images[node_id]:
            main_base64_string = image_to_base64(image_data)
            
    return main_base64_string
    

@app.post("/api/t2i")
async def handle_t2i_generation(request: QueryRequest):
    try:
        if request.query_type == "flux_t2i":
            image_base64_str = run_flux_t2i_workflow(request.input_prompt)
            response = QueryResponse(
                base64_imag_str=image_base64_str,
                status="success",
                error=None
            )
            return JSONResponse(content=response.dict())
        else:
            raise HTTPException(status_code=400, detail="Invalid query_type")
    except Exception as e:
        response = QueryResponse(
            base64_imag_str="",
            status="error",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=response.dict())
    

@app.get("/health")
async def health_check():
    return {"status": "healthy"}