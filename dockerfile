FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310-ubuntu20.04-sagemaker

RUN pip install --no-cache-dir fastapi uvicorn sagemaker
RUN curl -L https://github.com/peak/s5cmd/releases/download/v2.0.0/s5cmd_2.0.0_Linux-64bit.tar.gz | tar -xz && mv s5cmd /opt/conda/bin/

ENV PATH="/opt/program:${PATH}"
COPY code /opt/program

####install ComfyUI
COPY ComfyUI /opt/program
RUN pip install -r /opt/program/requirements.txt

####install relevant dependence
RUN pip install torchvision

###download relevant models
RUN /opt/conda/bin/s5cmd sync s3://sagemaker-us-west-2-687912291502/models/loras/ /opt/program/models/loras/
RUN /opt/conda/bin/s5cmd sync s3://sagemaker-us-west-2-687912291502/models/sd/ /opt/program/models/checkpoints/
RUN /opt/conda/bin/s5cmd sync s3://sagemaker-us-west-2-687912291502/models/clip_vision/ /opt/program/models/clip_vision/
RUN /opt/conda/bin/s5cmd sync s3://sagemaker-us-west-2-687912291502/models/controlnet/ /opt/program/models/controlnet/


###install relevant ComfyUI nodes
RUN git clone https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git /opt/program/custom_nodes/ComfyUI-Advanced-ControlNet
RUN git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git /opt/program/custom_nodes/ComfyUI-AnimateDiff-Evolved
RUN /opt/conda/bin/s5cmd sync s3://sagemaker-us-west-2-687912291502/models/animatediff/ /opt/program/custom_nodes/ComfyUI-AnimateDiff-Evolved/models/
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git /opt/program/custom_nodes/ComfyUI-VideoHelperSuite

####install relevant http/socket client（for unicorn web server）
RUN pip3 install websocket-client
RUN pip3 install -U requests
RUN pip3 install pydantic

#####start comfyui
RUN chmod 755 /opt/program
RUN nohup python3 /opt/program/main.py --listen 0.0.0.0 &
WORKDIR /opt/program
RUN chmod 755 serve