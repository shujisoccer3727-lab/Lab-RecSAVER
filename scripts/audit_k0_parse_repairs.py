"""保存済みk0失敗3件の読み取り専用監査。修復例は別ディレクトリに保存する。

標準ライブラリのみ使用。対象固有の修復を検証する監査スクリプトであり、
一般用途のrepair parserではない。元JSONLや実験の集計値を変更しない。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/full_prediction_experiment/predictions_k0.jsonl"
OUT = ROOT / "outputs/k0_parse_repair_audit"
TARGETS = ("3499:2", "3703:1", "5595:2")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, text):
    path.write_text(text, encoding="utf-8")


def main():
    before = sha(SOURCE)
    spec = importlib.util.spec_from_file_location("original_parser", ROOT / "src/recsaver/parsing.py")
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    metadata = json.loads((ROOT / "outputs/full_prediction_experiment/metadata.json").read_text(encoding="utf-8"))
    assert sha(ROOT / "src/recsaver/parsing.py") == metadata["source_sha256"]["parser"]
    records = {}
    with SOURCE.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            if row["target_id"] in TARGETS:
                assert row["target_id"] not in records
                records[row["target_id"]] = (line_number, row)
    assert set(records) == set(TARGETS)
    OUT.mkdir(exist_ok=True, parents=True)
    findings = []
    report = ["# k0 parse失敗3件の監査", "", "元出力は変更せず、最終attemptを修復判定の対象とする。初回出力も別途検証する。",
              "初回のtoken数およびfinish_reasonは元レコードに保存されていない。output_tokensは最終出力の値。", ""]
    for tid in TARGETS:
        line_number, row = records[tid]
        assert row["retry_count"] == 1 and len(row["raw_model_output_attempts"]) == 2
        assert row["raw_model_output"] == row["raw_model_output_attempts"][-1]
        stem = tid.replace(":", "_")
        write(OUT / f"{stem}.record.json", json.dumps(row, ensure_ascii=False, indent=2) + "\n")
        classification = "C" if tid == "5595:2" else "A"
        decision = "REGENERATE_REQUIRED" if classification == "C" else "SAFE_REPAIR"
        result = dict(target_id=tid, source_line=line_number, classification=classification, decision=decision,
                      parse_error=row["parse_error"], retry_count=row["retry_count"],
                      final_output_tokens=row["output_tokens"], initial_output_tokens=None,
                      finish_reason_recorded="finish_reason" in row, context_fit=row["context_fit"],
                      final_matches_last_attempt=True, attempts=[])
        report += [f"## target {tid}", "", f"判定：{classification} / {decision}", "",
                   f"根拠：`outputs/full_prediction_experiment/predictions_k0.jsonl:{line_number}`", "",
                   f"parse_error: `{row['parse_error']}`; retry_count: {row['retry_count']}; final output_tokens: {row['output_tokens']}", ""]
        for index, raw in enumerate(row["raw_model_output_attempts"], 1):
            prefix = f"{stem}.attempt_{index}"
            write(OUT / f"{prefix}.raw.txt", raw)
            if index == 2:
                write(OUT / f"{stem}.final.raw.txt", raw)
            attempt = dict(attempt=index, output_tokens=row["output_tokens"] if index == 2 else None)
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                attempt["json_error"] = dict(message=exc.msg, position=exc.pos, line=exc.lineno, column=exc.colno)
            else:
                raise AssertionError("unexpected valid raw JSON")
            try:
                parser.parse_prediction(raw, require_reasoning=True)
            except ValueError as exc:
                attempt["original_parser_error"] = str(exc)
            else:
                raise AssertionError("original parser unexpectedly accepted raw")
            report += [f"### attempt {index}" + ("（retry後・最終raw output全文）" if index == 2 else "（retry前・全文）"),
                       "", "```text", raw, "```", "", f"JSON診断：`{attempt['json_error']}`", ""]
            if decision == "SAFE_REPAIR":
                match = re.fullmatch(r'\{"predicted_overall": ([1-5]), "reasoning": "(.*)"\}', raw, re.S)
                assert match, "do not repair incomplete or unexpected envelopes"
                score, body = match.groups()
                if tid == "3499:2":
                    old, new = r"you\'er", "you'er"
                    assert body.count(old) == 1 and '"' not in body
                    fixed = raw.replace(old, new)
                    expected_reasoning = body.replace(old, new)
                    edit = "Delete the single backslash before the apostrophe in you\\'er; preserve all other characters."
                    assert len(raw) - len(fixed) == 1
                else:
                    old, new = '"qualify"', r'\"qualify\"'
                    assert body.count(old) == 1 and body.count('"') == 2 and "\\" not in body
                    fixed = raw.replace(old, new)
                    expected_reasoning = body
                    edit = 'Escape only the two double quotes around qualify; preserve the decoded reasoning exactly.'
                    assert len(fixed) - len(raw) == 2
                value = json.loads(fixed)
                parsed = parser.parse_prediction(fixed, require_reasoning=True)
                assert value == parsed == {"predicted_overall": int(score), "reasoning": expected_reasoning}
                write(OUT / f"{prefix}.repaired.json", fixed)
                if index == 2:
                    write(OUT / f"{stem}.final.repaired.json", fixed)
                attempt.update(edit=edit, repaired_overall=value["predicted_overall"],
                               original_parser_accepts_repair=True, expected_reasoning_equal=True)
                report += ["最小修復：" + edit, "", "```json", fixed, "```", "",
                           "検証：既存parse_prediction()に成功。期待するreasoning本文との文字列一致をassert。", ""]
            else:
                assert not raw.endswith('"}')
                attempt.update(repair_attempted=False, reason="Reasoning is unfinished; do not append or infer missing content.")
                report += ["Reasoningが反復途中で終了しているため修復しない。最終出力は設定上限384 tokens。finish_reason自体は未保存。", ""]
            result["attempts"].append(attempt)
        findings.append(result)
    after = sha(SOURCE)
    assert before == after, "source must remain unchanged"
    audit = dict(source=str(SOURCE.relative_to(ROOT)), source_sha256=before, source_unchanged=before == after,
                 parser_sha256=sha(ROOT / "src/recsaver/parsing.py"), parser_matches_experiment_metadata=True,
                 validation="Python json.loads and existing parse_prediction(require_reasoning=True)",
                 findings=findings, safe_repair_count=2, manual_recoverable_count=0, regenerate_required_count=1)
    write(OUT / "audit.json", json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    write(OUT / "report.md", "\n".join(report))
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
