from pathlib import Path


root=Path(__file__).resolve().parents[1]
source=(root/'src/recsaver/feedback_development_engine_v21.py').read_text(encoding='utf-8')
source=source.replace('class Engine:', 'from .feedback_payload_compaction import intern_payload\n\nclass Engine:')
source=source.replace("prompt=template+json.dumps(payload,ensure_ascii=False,separators=(',',':'))", """encoded=intern_payload(payload) if stage in ['merge','integrate','compare','text'] else payload
            if encoded is not payload:
                name=key.replace(':','_').replace('|','__')+'.json'
                save(self.out/'stage_inputs_expanded'/stage/name,payload)
                save(self.out/'stage_inputs'/stage/name,encoded)
                append(self.out/'compaction_checks.jsonl',dict(stage=stage,key=key,lossless_roundtrip=True,
                    original_characters=len(json.dumps(payload,ensure_ascii=False)),serialized_characters=len(json.dumps(encoded,ensure_ascii=False))))
            prompt=template+json.dumps(encoded,ensure_ascii=False,separators=(',',':'))""")
(root/'src/recsaver/feedback_development_engine_v22.py').write_text(source,encoding='utf-8')
