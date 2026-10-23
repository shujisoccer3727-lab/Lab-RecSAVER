"""保存済み共通targetから主指標・分布・paired集計を独立に検算する。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1]/'outputs/full_prediction_main_results'


def main():
    targets = pd.read_csv(OUT/'common_targets.csv')
    audit = pd.read_csv(OUT/'intersection_audit.csv')
    results = pd.read_csv(OUT/'main_5condition_results.csv')
    paired = pd.read_csv(OUT/'paired_comparisons.csv')
    ci = pd.read_csv(OUT/'bootstrap_ci.csv')
    metadata = json.loads((OUT/'metadata.json').read_text())
    n = len(targets)
    assert n == metadata['common_target_count'] == audit.included_in_common_set.sum()
    assert set(targets.target_id) == set(audit.loc[audit.included_in_common_set,'target_id'])
    assert not targets.target_id.duplicated().any()
    assert not targets.duplicated(['source_row_id','target_rater']).any()
    assert audit.filter(like='available_').all(axis=1).equals(audit.included_in_common_set)
    g = targets.gold_overall.to_numpy()
    prediction_columns = [c for c in targets if c.startswith('prediction_')]
    predictions = {}
    for col,r in zip(prediction_columns,results.itertuples()):
        p = targets[col].to_numpy()
        predictions[r.Condition] = p
        assert np.isin(p,[1,2,3,4,5]).all() and r.N == n
        # QWK = 1 − 観測MSE / 独立周辺分布下の期待MSE。
        expected_mse = np.mean(g*g)+np.mean(p*p)-2*np.mean(g)*np.mean(p)
        values = [np.mean(g==p),np.mean(abs(g-p)),np.sqrt(np.mean((g-p)**2)),1-np.mean((g-p)**2)/expected_mse]
        np.testing.assert_allclose(values,[r.Accuracy,r.MAE,r.RMSE,r.QWK],rtol=1e-12)
    for r in paired.itertuples():
        delta = abs(predictions[r.from_condition]-g)-abs(predictions[r.to_condition]-g)
        assert (r.improved,r.unchanged,r.worsened) == ((delta>0).sum(),(delta==0).sum(),(delta<0).sum())
        np.testing.assert_allclose(delta.mean(),r.mean_paired_ae_difference)
        np.testing.assert_allclose(delta.mean(),-r.mae_delta)
        for c in ci[ci.analysis==r.comparison].itertuples():
            point = r.mean_paired_ae_difference if c.statistic=='paired_ae_difference' else getattr(r,c.statistic)
            np.testing.assert_allclose(point,c.point_estimate)
            assert c.ci_lower <= c.ci_upper and c.n == n
    assert len(ci)==24 and len(paired)==6
    distribution = pd.read_csv(OUT/'prediction_distribution_common.csv')
    assert distribution.groupby('Condition')['count'].sum().eq(n).all()
    np.testing.assert_allclose(distribution.groupby('Condition').proportion.sum(),1)
    raters = pd.read_csv(OUT/'rater_summary.csv')
    assert raters.groupby('Condition').N.sum().eq(n).all()
    assert raters.groupby('Condition').target_rater.nunique().eq(27).all()
    gs = pd.read_csv(OUT/'gold_score_summary.csv')
    assert gs.groupby('Condition').N.sum().eq(n).all()
    gd = pd.read_csv(OUT/'gold_score_prediction_distribution.csv')
    assert gd.groupby(['Condition','gold_overall'])['count'].sum().equals(gs.set_index(['Condition','gold_overall']).N.sort_index())
    pairs = pd.read_csv(OUT/'same_essay_pair_analysis.csv')
    group_sizes = targets.groupby('source_row_id').size()
    assert pairs.same_essay_rater_pair_count.eq((group_sizes*(group_sizes-1)//2).sum()).all()
    assert pairs.gold_disagreement_pair_count.nunique()==1
    print(f'PASS: common N={n}; independent metrics, 6 comparisons, 24 CIs, distributions, 27 raters, same-essay pair counts.')


if __name__ == '__main__':
    main()
