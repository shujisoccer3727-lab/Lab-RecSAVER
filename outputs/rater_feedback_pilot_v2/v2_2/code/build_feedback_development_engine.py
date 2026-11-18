"""既存Engineを別ファイルへ保存し、JSON schema供給先だけ切り替える。"""
import inspect
from src.recsaver.rater_feedback_pilot_v2 import ROOT, Engine


def main():
    source=inspect.getsource(Engine).replace('from .feedback_output_schema import output_schema',
                                          'from .feedback_development_schema import output_schema')
    header='''"""v1.6 Engineの別コピー。変更はschema供給先のみ。既存成果物は変更しない。"""
import json
import subprocess
import time
from .rater_feedback_pilot_v2 import ROOT, now, digest, load, save, append, parse_json

'''
    path=ROOT/'src/recsaver/feedback_development_engine.py'
    assert not path.exists(), 'Do not silently replace an existing engine revision'
    path.write_text(header+source,encoding='utf-8')


if __name__=='__main__': main()
