algorithm_name=comfyui-inference

account=$(aws sts get-caller-identity --query Account --output text)

# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)

fullname="${account}.dkr.ecr.${region}.amazonaws.com/${algorithm_name}:latest"

# If the repository doesn't exist in ECR, create it.

aws ecr describe-repositories --repository-names "${algorithm_name}" > /dev/null 2>&1
if [ $? -ne 0 ]
then
aws ecr create-repository --repository-name "${algorithm_name}" > /dev/null
fi

#load public ECR image
#aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

# Log into Docker
pwd=$(aws ecr get-login-password --region ${region})
docker login --username AWS -p ${pwd} ${account}.dkr.ecr.${region}.amazonaws.com

# Build the docker image locally with the image name and then push it to ECR
# with the full name.
#git clone https://github.com/comfyanonymous/ComfyUI.git
#docker build -t ${algorithm_name}  ./ -f ./docker/dockerfile-simple

#git clone -b dev https://github.com/qingyuan18/ComfyUI.git
#docker build -t ${algorithm_name}  ./ -f ./docker/dockerfile-dev

#git clone -b latest https://github.com/qingyuan18/ComfyUI.git
#docker build -t ${algorithm_name}  ./ -f ./docker/dockerfile-latest


git clone -b flux https://github.com/qingyuan18/ComfyUI.git
dockerfile="./docker/dockerfile-flux"
# 如果提供了参数，则使用该参数作为 Dockerfile 名称
if [ $# -eq 1 ]; then
    dockerfile=$1
fi
# 构建 Docker 镜像
docker build -t ${algorithm_name} ./ -f ./${dockerfile}
#docker build -t ${algorithm_name}  ./ -f ./docker/dockerfile-flux

docker tag ${algorithm_name} ${fullname}
docker push ${fullname}
rm -rf ./ComfyUI