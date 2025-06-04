
## upgrade lib
cd /tmp/ && git clone https://github.com/thu-ml/SageAttention.git && cd SageAttention && pip install -e .

## download models
mkdir -p /tmp/models && cd /tmp/models/
git clone https://github.com/Tencent/HunyuanVideo.git
huggingface-cli download tencent/HunyuanVideo --local-dir /tmp/models/hunyuan_ckpts

#### llava-llama
cd /tmp/models/hunyuan_ckpts
huggingface-cli download xtuner/llava-llama-3-8b-v1_1-transformers --local-dir ./llava-llama-3-8b-v1_1-transformers

#### 只需要llava-llama的text encoder
cd /tmp/models/hunyuan_ckpts
python /tmp/models/HunyuanVideo/hyvideo/utils/preprocess_text_encoder_tokenizer_utils.py \
       --input_dir /tmp/models/hunyuan_ckpts/llava-llama-3-8b-v1_1-transformers \
       --output_dir /tmp/models/hunyuan_ckpts/text_encoder


cd /tmp/models/hunyuan_ckpts
huggingface-cli download openai/clip-vit-large-patch14 --local-dir /tmp/models/hunyuan_ckpts/text_encoder_2

#### vae
mkdir -p /tmp/models/hunyuan_ckpts/vae \
         && cd /tmp/models/hunyuan_ckpts/vae/ \
         && wget https://huggingface.co/tencent/HunyuanVideo/resolve/main/hunyuan-video-t2v-720p/vae/pytorch_model.pt


##cache captions & image latents
cd /opt/ml/code/
python cache_latents.py --dataset_config /opt/ml/input/data/lora_hunyuan/dataset.toml \
                        --vae /tmp/models/hunyuan_ckpts/vae/pytorch_model.pt \
                        --vae_chunk_size 32 --vae_tiling


python cache_text_encoder_outputs.py --dataset_config /opt/ml/input/data/lora_hunyuan/dataset.toml  \
                        --text_encoder1 /tmp/models/hunyuan_ckpts/text_encoder \
                        --text_encoder2 /tmp/models/hunyuan_ckpts/text_encoder_2 \
                        --batch_size 16

## start train
accelerate launch --num_cpu_threads_per_process 1 --mixed_precision bf16 hv_train_network.py \
    --dit /tmp/models/hunyuan_ckpts/hunyuan-video-t2v-720p/transformers/mp_rank_00_model_states_fp8.pt \
    --dataset_config /opt/ml/input/data/lora_hunyuan/dataset.toml --sage_attn --split_attn --mixed_precision bf16 --fp8_base \
    --optimizer_type adamw --learning_rate 6e-4 --lr_scheduler cosine_with_restarts  --gradient_checkpointing  \
    --max_data_loader_n_workers 4 --persistent_data_loader_workers  \
    --network_module networks.lora --network_dim 32 --network_alpha 32 \
    --timestep_sampling sigmoid --discrete_flow_shift 1 \
    --max_train_epochs 300 --save_every_n_epochs 100 --seed 0 \
    --output_dir /opt/ml/model/lora_hunyuan --output_name hunyuan-lora
