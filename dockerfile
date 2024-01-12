FROM 763104351884.dkr.ecr.us-west-2.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu118-ubuntu20.04-sagemaker

RUN pip install --no-cache-dir fastapi uvicorn sagemaker
RUN curl -L https://github.com/peak/s5cmd/releases/download/v2.0.0/s5cmd_2.0.0_Linux-64bit.tar.gz | tar -xz && mv s5cmd /opt/conda/bin/

ENV PATH="/opt/program:${PATH}"
COPY code /opt/program

####install ComfyUI
COPY ComfyUI /opt/program
RUN pip install -r /opt/program/requirements.txt

####upgrade torch/torchversion/cuda121 relevant dependence
RUN pip install torch torchvision --upgrade --index-url https://download.pytorch.org/whl/cu121

###download relevant models
RUN wget https://civitai.com/api/download/models/34433
RUN wget https://huggingface.co/nergaldarski/CardosAnimeV2.0/resolve/main/cardosAnime_v20.safetensors
RUN wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
RUN wget https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors
RUN wget https://huggingface.co/lllyasviel/ControlNet/resolve/main/models/control_sd15_canny.pth
RUN wget https://huggingface.co/lllyasviel/ControlNet/resolve/main/models/control_sd15_depth.pth
RUN wget https://huggingface.co/lllyasviel/ControlNet/resolve/main/models/control_sd15_openpose.pth
RUN wget https://huggingface.co/lllyasviel/ControlNet/resolve/main/models/control_sd15_scribble.pth
RUN wget https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11f1e_sd15_tile.pth
RUN wget https://huggingface.co/lllyasviel/ControlNet-v1-1/resolve/main/control_v11p_sd15_lineart.pth
RUN wget https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15.ckpt
RUN wget https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt
RUN wget https://huggingface.co/guoyww/animatediff/resolve/main/v2_lora_TiltDown.ckpt
RUN wget https://huggingface.co/guoyww/animatediff/resolve/main/v2_lora_PanRight.ckpt
RUN wget https://huggingface.co/guoyww/animatediff/resolve/main/v2_lora_RollingAnticlockwise.ckpt
RUN wget https://huggingface.co/mmmoof1/vae-ft-mse-840000-ema-pruned/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors
RUN wget https://huggingface.co/latent-consistency/lcm-lora-sdv1-5/resolve/main/pytorch_lora_weights.safetensors

RUN mv ./vae*.safetensors /opt/program/models/vae/
RUN mv ./pytorch_lora_weights.safetensors  /opt/program/models/loras/
RUN mv ./*.safetensors /opt/program/models/checkpoints/
RUN mv ./34433 /opt/program/models/loras/promptsgirl_v3.safetensors
RUN mv ./*.pth /opt/program/models/controlnet/



###install relevant ComfyUI nodes
RUN git clone https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git /opt/program/custom_nodes/ComfyUI-Advanced-ControlNet

RUN git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git /opt/program/custom_nodes/ComfyUI-AnimateDiff-Evolved
RUN mv ./mm_sd*.ckpt /opt/program/custom_nodes/ComfyUI-AnimateDiff-Evolved/models/
RUN mv ./v2_lora*.ckpt /opt/program/custom_nodes/ComfyUI-AnimateDiff-Evolved/motion_lora/

RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git /opt/program/custom_nodes/ComfyUI-VideoHelperSuite

####install relevant http/socket client（for unicorn web server）
RUN pip3 install websocket-client
RUN pip3 install -U requests
RUN pip3 install pydantic

#####start comfyui
RUN chmod 755 /opt/program
WORKDIR /opt/program
RUN chmod 755 serve