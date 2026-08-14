"""1つのmax_model_lenでモデルロードと短文推論を行い、JSON結果を保存する。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import traceback

os.environ["VLLM_USE_V1"] = "0"
os.environ["VLLM_ENABLE_V1_ENGINE"] = "0"


def gpu_memory_mib() -> dict:
    try:
        import pynvml
        pynvml.nvmlInit()
        info = pynvml.nvmlDeviceGetMemoryInfo(pynvml.nvmlDeviceGetHandleByIndex(0))
        return {"gpu_memory_used_mib": round(info.used / 1024**2, 1),
                "gpu_memory_total_mib": round(info.total / 1024**2, 1)}
    except Exception as exc:
        return {"gpu_memory_used_mib": None, "gpu_memory_total_mib": None,
                "gpu_memory_query_error": f"{type(exc).__name__}: {exc}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-model-len", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"max_model_len": args.max_model_len,
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "model_load_success": False, "inference_success": False,
              "oom": False, "error": None, **gpu_memory_mib()}
    try:
        from vllm import LLM, SamplingParams
        llm = LLM(model="Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4",
                  quantization="gptq_marlin", tensor_parallel_size=1,
                  max_model_len=args.max_model_len, gpu_memory_utilization=0.90,
                  trust_remote_code=True)
        result["model_load_success"] = True
        result.update({f"after_load_{k}": v for k, v in gpu_memory_mib().items()})
        output = llm.generate(["Reply with exactly: OK"],
                              SamplingParams(temperature=0.0, max_tokens=8), use_tqdm=False)
        result["inference_success"] = bool(output and output[0].outputs)
        result["test_output"] = output[0].outputs[0].text if output else None
        result.update({f"after_inference_{k}": v for k, v in gpu_memory_mib().items()})
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        result["error"] = message
        result["oom"] = "out of memory" in message.lower() or "cuda oom" in message.lower()
        result["traceback_tail"] = traceback.format_exc()[-4000:]
        result.update({f"after_error_{k}": v for k, v in gpu_memory_mib().items()})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
