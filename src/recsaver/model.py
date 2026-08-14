from __future__ import annotations

import os
os.environ["VLLM_USE_V1"] = "0"
os.environ["VLLM_ENABLE_V1_ENGINE"] = "0"


class VLLMGenerator:
    def __init__(self, config: dict):
        from vllm import LLM
        model = config["model"]
        self.llm = LLM(
            model=model["model_id"], quantization=model["quantization"],
            tensor_parallel_size=model["tensor_parallel_size"], max_model_len=model["max_model_len"],
            gpu_memory_utilization=model["gpu_memory_utilization"], trust_remote_code=True,
        )
        self.tokenizer = self.llm.get_tokenizer()

    def generate(self, prompts: list[str], parameters: dict, n: int = 1) -> list[list[str]]:
        from vllm import SamplingParams
        chat_prompts = [
            self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=False, add_generation_prompt=True
            ) for prompt in prompts
        ]
        params = SamplingParams(n=n, **parameters)
        outputs = self.llm.generate(chat_prompts, params, use_tqdm=True)
        return [[item.text for item in output.outputs] for output in outputs]
