
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

@dataclass
class RiskItem:
    name: str
    severity: str
    detail: str
    evidence: Dict
    def to_dict(self): return asdict(self)

def detect_target_leakage(df: pd.DataFrame, target: str) -> List[RiskItem]:
    """检测目标泄漏：数值列与目标的高相关、分类纯度异常"""
    risks: List[RiskItem] = []
    y = df[target].values
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target in num_cols:
        num_cols.remove(target)
    suspicious: List[Tuple[str, float]] = []
    for c in num_cols:
        x = df[c].values
        if np.std(x) == 0: continue
        try:
            corr = np.corrcoef(x, y)[0, 1]
        except Exception:
            continue
        if np.isfinite(corr) and abs(corr) >= 0.98:
            suspicious.append((c, float(corr)))
    for c in num_cols:
        x = df[[c]].values
        if np.std(x) == 0: continue
        lr = LinearRegression().fit(x, y)
        r2 = lr.score(x, y)
        if np.isfinite(r2) and r2 >= 0.98 and (c, r2) not in suspicious:
            suspicious.append((c, float(r2)))
    if suspicious:
        details = {c: v for c, v in suspicious}
        risks.append(RiskItem(
            name="Target leakage (high correlation)",
            severity="high",
            detail="以下列与目标高度相关（|corr|或R²≥0.98），可能泄漏。",
            evidence={"columns": details},
        ))
    # categorical purity
    cat_cols = [c for c in df.columns if c not in num_cols + [target]]
    purity_hits = {}
    for c in cat_cols:
        vc = df[c].value_counts(dropna=False)
        if len(vc) < max(10, int(len(df) * 0.01)):
            grp = df.groupby(c)[target].mean()
            sizes = df.groupby(c)[target].size()
            for k, p in grp.items():
                if sizes[k] >= 20 and (p <= 0.02 or p >= 0.98):
                    purity_hits.setdefault(c, []).append({"value": str(k), "p": float(p), "n": int(sizes[k])})
    if purity_hits:
        risks.append(RiskItem(
            name="Target leakage (categorical purity)",
            severity="medium",
            detail="某些类别几乎完美预测目标，若由聚合统计得来可能泄漏。",
            evidence={"columns": purity_hits},
        ))
    return risks

def detect_kfold_group_leakage(df: pd.DataFrame, target: str) -> List[RiskItem]:
    """检测KFold泄漏预警：高重复/低唯一度列"""
    risks: List[RiskItem] = []
    n = len(df)
    group_candidates = []
    for c in df.columns:
        if c == target: continue
        nunique = df[c].nunique(dropna=False)
        if 1 < nunique < n * 0.2:
            dup_rate = 1 - nunique / n
            group_candidates.append({"column": c, "nunique": int(nunique), "dup_rate": float(dup_rate)})
    if group_candidates:
        risks.append(RiskItem(
            name="KFold leakage risk (use GroupKFold)",
            severity="medium",
            detail="这些高重复列建议用作 groups 以避免跨折泄漏。",
            evidence={"candidates": group_candidates},
        ))
    return risks

def detect_time_column_issues(df: pd.DataFrame, time_col: Optional[str]) -> List[RiskItem]:
    """检测时间列解析与时间感知建议"""
    risks: List[RiskItem] = []
    if not time_col: return risks
    if time_col not in df.columns:
        risks.append(RiskItem("Time column missing", "high", f"时间列 `{time_col}` 不存在。", {}))
        return risks
    t = pd.to_datetime(df[time_col], errors="coerce")
    miss = int(t.isna().sum())
    if miss > 0:
        risks.append(RiskItem("Time parse errors", "medium", f"`{time_col}` 有 {miss} 个无效值。", {"invalid": miss}))
    if t.notna().any():
        risks.append(RiskItem("Time-awareness suggestion", "low",
                              "建议使用时间感知切分/编码并校验口径一致。",
                              {"min": str(t.min()), "max": str(t.max())}))
    return risks

def run_checks(df: pd.DataFrame, target: str, time_col: Optional[str]) -> Dict:
    """运行所有检测 - v0.1版本"""
    risks = []
    risks += detect_target_leakage(df, target)
    risks += detect_kfold_group_leakage(df, target)
    risks += detect_time_column_issues(df, time_col)
    return {"risks": [r.to_dict() for r in risks]}

