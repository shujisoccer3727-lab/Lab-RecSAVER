param([string]$RepoRoot = (Split-Path $PSScriptRoot -Parent))
$ErrorActionPreference = 'Stop'
$raw = @(Import-Csv -Encoding UTF8 (Join-Path $RepoRoot 'data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv'))
$wide = @(Import-Csv -Encoding UTF8 (Join-Path $RepoRoot 'data/processed/rater_essay_wide.csv'))
$traits = @('Overall','Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions')
$invalid = @($wide | Where-Object { $row = $_; @($traits | Where-Object { $row.$_ -notmatch '^[1-5](\.0)?$' }).Count -gt 0 })
$manifest = @(Get-Content -Encoding UTF8 (Join-Path $RepoRoot 'outputs/full_prediction_experiment/target_manifest.jsonl') | ForEach-Object { $_ | ConvertFrom-Json })
$historyIssues = @()
foreach ($row in $manifest) {
    $targetRaw = $raw[[int]$row.source_row_id]
    foreach ($kind in @('correct','wrong')) {
        foreach ($hid in $row.($kind + '_history_ids')) {
            $source = [int]($hid.Split(':')[0])
            $historyRaw = $raw[$source]
            if ($source -eq [int]$row.source_row_id -or $historyRaw.Filename -ceq $targetRaw.Filename -or $historyRaw.Text -ceq $targetRaw.Text) {
                $historyIssues += [pscustomobject]@{target_id=$row.target_id; kind=$kind; history_id=$hid; same_source=($source -eq [int]$row.source_row_id); same_filename=($historyRaw.Filename -ceq $targetRaw.Filename); same_text=($historyRaw.Text -ceq $targetRaw.Text)}
            }
        }
    }
}
$hashChecks = @()
foreach ($experiment in @('full_prediction_experiment','reasoning_eval_large')) {
    $md = Get-Content -Raw -Encoding UTF8 (Join-Path $RepoRoot "outputs/$experiment/metadata.json") | ConvertFrom-Json
    foreach ($property in $md.source_paths.PSObject.Properties) {
        $expected = $md.source_sha256.($property.Name)
        $path = Join-Path $RepoRoot $property.Value
        $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
        $hashChecks += [pscustomobject]@{experiment=$experiment; key=$property.Name; path=$property.Value; matches=($expected -eq $actual)}
    }
}
$failures = @()
$conditionCounts = @()
$common = $null
foreach ($name in @('predictions_k0','predictions_k0_rubric','predictions_correct_k3_rubric','predictions_wrong_k3_rubric')) {
    $ids = [System.Collections.Generic.HashSet[string]]::new()
    $lineNumber = 0
    $retryCount = 0
    Get-Content -Encoding UTF8 (Join-Path $RepoRoot "outputs/full_prediction_experiment/$name.jsonl") | ForEach-Object {
        $lineNumber++
        $record = $_ | ConvertFrom-Json
        $retryCount += $record.retry_count
        if ($record.parse_success) { [void]$ids.Add($record.target_id) }
        else { $failures += [pscustomobject]@{file=$name; line=$lineNumber; target_id=$record.target_id; parse_error=$record.parse_error; retry_count=$record.retry_count; context_fit=$record.context_fit; output_tokens=$record.output_tokens} }
    }
    if ($null -eq $common) { $common = [System.Collections.Generic.HashSet[string]]::new($ids) } else { $common.IntersectWith($ids) }
    $conditionCounts += [pscustomobject]@{file=$name; rows=$lineNumber; successful=$ids.Count; retries=$retryCount}
}
$summary = @(Import-Csv (Join-Path $RepoRoot 'outputs/reasoning_eval_large/target_reference_summary.csv'))
$pool = @(Get-Content -Encoding UTF8 (Join-Path $RepoRoot 'outputs/reasoning_eval_large/verified_reference_pool.jsonl') | ForEach-Object { $_ | ConvertFrom-Json })
$audit = [ordered]@{
    raw_rows=$raw.Count
    raw_unique_filename=@($raw.Filename | Sort-Object -Unique).Count
    raw_unique_text=@($raw.Text | Sort-Object -Unique -CaseSensitive).Count
    same_rater_both_positions=@($raw | Where-Object { $_.Rater_1 -eq $_.Rater_2 }).Count
    wide_rows=$wide.Count
    valid_rows=($wide.Count-$invalid.Count)
    invalid_rows=$invalid.Count
    invalid_score_values=@($invalid | ForEach-Object { $row=$_; foreach ($trait in $traits) { if ($row.$trait -notmatch '^[1-5](\.0)?$') { $row.$trait } } } | Sort-Object -Unique)
    rater_count=@($wide.rater_id | Sort-Object -Unique).Count
    history_overlap_records=$historyIssues
    source_hash_checks=$hashChecks
    prediction_condition_counts=$conditionCounts
    prediction_common_count=$common.Count
    prediction_failures=$failures
    reasoning_target_count=$summary.Count
    reasoning_covered_count=@($summary | Where-Object { [int]$_.verified_count -gt 0 }).Count
    reasoning_pool_rows=$pool.Count
    reasoning_pool_targets=@($pool.target_id | Sort-Object -Unique).Count
    reasoning_pool_gold_mismatch=@($pool | Where-Object { $_.reconstructed_overall -ne $_.gold_overall }).Count
}
$outDir = Join-Path $RepoRoot 'outputs/jima_conditions_audit'
[void](New-Item -ItemType Directory -Force -Path $outDir)
$audit | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $outDir 'audit.json')
$audit | ConvertTo-Json -Depth 8
