"""GPU-only execution; no downloads, truncation, output repair or implicit regeneration."""
import os
import sys
import traceback
from .pair_feedback import ROOT, read, save, sha, now, generation_seed, strict_json, schema


class Engine:
    def __init__(self, cfg, out):
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', VLLM_USE_V1='0', VLLM_ENABLE_V1_ENGINE='0')
        import torch, transformers, vllm
        from transformers import AutoTokenizer
        from huggingface_hub import snapshot_download
        self.cfg, self.out, self.llm = cfg, out, None
        self.path = snapshot_download(cfg['model']['model_id'], local_files_only=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.path, local_files_only=True)
        save(out / 'environment.json', dict(time=now(), python=sys.version, torch=torch.__version__,
             transformers=transformers.__version__, vllm=vllm.__version__, cuda=torch.cuda.is_available(),
             gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, model_snapshot=self.path))

    def rendered(self, stage, payload):
        template = (ROOT / self.cfg['prompts'][str(stage)]).read_text(encoding='utf-8')
        assert template.count('{{INPUT_JSON}}') == 1
        prompt = template.replace('{{INPUT_JSON}}', __import__('json').dumps(payload, ensure_ascii=False, allow_nan=False))
        messages = [dict(role='user', content=prompt)]
        chat = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return template, messages, chat

    def fits(self, stage, payload):
        chat = self.rendered(stage, payload)[2]
        return len(self.tokenizer.encode(chat, add_special_tokens=False)) + self.cfg['max_tokens'][str(stage)] <= self.cfg['model']['max_model_len']

    def parse(self, folder, stage, payload, template):
        raw = (folder / 'raw.txt').read_text(encoding='utf-8')
        json_valid = False
        try:
            value = strict_json(raw)
            json_valid = True
            save(folder / 'parsed.json', value)
            errors = schema(stage, value, payload, template)
        except Exception as ex:
            errors = [str(ex)]
        save(folder / 'result.json', dict(json_valid=json_valid, schema_valid=json_valid and not errors, errors=errors,
                                          raw_sha256=sha(folder / 'raw.txt'), reparsed_original_only=True))

    def run(self, stage, jobs, dry=False):
        pending = []
        for key, payload in jobs:
            folder = self.out / f'stage{stage}' / key
            template, messages, chat = self.rendered(stage, payload)
            if (folder / 'input.json').exists():
                assert read(folder / 'input.json') == payload, 'Saved input differs: ' + key
            if (folder / 'result.json').exists() or (folder / 'error.json').exists():
                continue
            if (folder / 'raw.txt').exists():
                self.parse(folder, stage, payload, template)
                continue
            params = dict(self.cfg['generation'], max_tokens=self.cfg['max_tokens'][str(stage)], seed=generation_seed(self.cfg, stage, key))
            count = len(self.tokenizer.encode(chat, add_special_tokens=False))
            save(folder / 'input.json', payload)
            save(folder / 'messages.json', messages)
            save(folder / 'sampling.json', params)
            save(folder / 'context_check.json', dict(prompt_tokens=count, output_budget=params['max_tokens'],
                 context_limit=self.cfg['model']['max_model_len'], fits=count + params['max_tokens'] <= self.cfg['model']['max_model_len'],
                 truncated=False, prompt_path=self.cfg['prompts'][str(stage)], prompt_sha256=sha(ROOT / self.cfg['prompts'][str(stage)])))
            (folder / 'rendered_chat.txt').write_text(chat, encoding='utf-8')
            if count + params['max_tokens'] > self.cfg['model']['max_model_len']:
                save(folder / 'error.json', dict(kind='context_capacity', time=now(), generated=False))
                continue
            pending.append((folder, payload, template, chat, params))
        if dry or not pending:
            return
        from vllm import LLM, SamplingParams
        if self.llm is None:
            model = dict(self.cfg['model'])
            model.pop('model_id')
            options = model.pop('runtime_options', {})
            self.llm = LLM(model=self.path, trust_remote_code=True, **model, **options)
        for start in range(0, len(pending), self.cfg['batch_size']):
            batch = pending[start:start + self.cfg['batch_size']]
            for folder, *_ in batch:
                save(folder / 'attempt.json', dict(started=now(), state='running_or_interrupted', pid=os.getpid()))
            try:
                outputs = self.llm.generate([x[3] for x in batch], [SamplingParams(**x[4]) for x in batch], use_tqdm=True)
            except BaseException:
                save(self.out / 'interruption.json', dict(time=now(), stage=stage, keys=[x[0].name for x in batch], traceback=traceback.format_exc()))
                raise
            for (folder, payload, template, _, params), output in zip(batch, outputs):
                item = output.outputs[0]
                (folder / 'raw.txt').write_text(item.text, encoding='utf-8')
                save(folder / 'generation.json', dict(finished=now(), seed=params['seed'], finish_reason=item.finish_reason,
                     prompt_tokens=len(output.prompt_token_ids), output_tokens=len(item.token_ids), raw_sha256=sha(folder / 'raw.txt')))
                self.parse(folder, stage, payload, template)
                save(folder / 'attempt.json', dict(state='completed', finished=now(), pid=os.getpid()))
            save(self.out / 'progress.json', dict(time=now(), stage=stage, completed_in_this_call=min(start + len(batch), len(pending)), total_pending_at_start=len(pending)))
