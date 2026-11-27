import json
import sys
from pathlib import Path
import torch, transformers, vllm
from huggingface_hub import snapshot_download
out = Path(__file__).resolve().parents[1] / 'outputs/pair_feedback_20261126'
out.mkdir(parents=True, exist_ok=True)
data = dict(python=sys.version, torch=torch.__version__, transformers=transformers.__version__,
            vllm=vllm.__version__, cuda=torch.cuda.is_available(),
            gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            model_snapshot=snapshot_download('Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4', local_files_only=True))
(out / 'environment.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
print(json.dumps(data, indent=2))
