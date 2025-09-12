
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

def detect_target_encoding_leakage(df: pd.DataFrame, target: str, time_col: Optional[str]) -> List[RiskItem]:
    """检测 target encoding/WOE/滚动统计类泄漏"""
    risks: List[RiskItem] = []
    y = df[target].values
    
    # 检测可能的 target encoding 特征
    te_suspects = {}
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if target in num_cols:
        num_cols.remove(target)
    if time_col and time_col in num_cols:
        num_cols.remove(time_col)
    
    for c in num_cols:
        x = df[c].values
        if np.std(x) == 0: continue
        
        # 检查是否像 target encoding（值域在 [0,1] 或接近 target 均值）
        target_mean = np.mean(y)
        if (np.min(x) >= 0 and np.max(x) <= 1) or (abs(np.mean(x) - target_mean) < 0.1):
            try:
                corr = np.corrcoef(x, y)[0, 1]
                if np.isfinite(corr) and abs(corr) >= 0.7:  # 降低阈值检测 TE 特征
                    te_suspects[c] = {"corr": float(corr), "mean": float(np.mean(x)), "target_mean": float(target_mean)}
            except Exception:
                continue
    
    if te_suspects:
        risks.append(RiskItem(
            name="Target encoding leakage risk",
            severity="high",
            detail="以下列疑似 target encoding 特征，与目标高相关且值域可疑。",
            evidence={"columns": te_suspects},
        ))
    
    # 检测时间窗口泄漏（如果有时间列）
    if time_col and time_col in df.columns:
        t = pd.to_datetime(df[time_col], errors="coerce")
        if t.notna().any():
            # 检查是否有全量统计特征（应该是窗口内统计）
            window_suspects = {}
            for c in num_cols:
                if c in te_suspects: continue  # 已经检测过的跳过
                x = df[c].values
                if np.std(x) == 0: continue
                
                # 检查是否像全量统计：方差很小（统计值变化不大）
                cv = np.std(x) / (np.mean(x) + 1e-8)  # 变异系数
                if cv < 0.1:  # 变异系数很小，可能是全量统计
                    try:
                        corr = np.corrcoef(x, y)[0, 1]
                        if np.isfinite(corr) and abs(corr) >= 0.3:
                            window_suspects[c] = {"corr": float(corr), "cv": float(cv)}
                    except Exception:
                        continue
            
            if window_suspects:
                risks.append(RiskItem(
                    name="Time window leakage risk",
                    severity="high",
                    detail="以下列疑似使用全量统计而非窗口内统计，存在时间泄漏风险。",
                    evidence={"columns": window_suspects, "suggestion": "应使用仅窗口内可见的统计"},
                ))
    
    return risks

def detect_kfold_group_leakage(df: pd.DataFrame, target: str) -> List[RiskItem]:
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

def detect_cv_consistency_issues(df: pd.DataFrame, target: str, time_col: Optional[str], cv_type: Optional[str]) -> List[RiskItem]:
    """检测 CV 口径一致性问题"""
    risks: List[RiskItem] = []
    
    # 分析数据特征，给出 CV 建议
    n = len(df)
    has_time = time_col and time_col in df.columns
    has_groups = False
    group_cols = []
    
    # 检查是否有明显的分组结构
    for c in df.columns:
        if c == target or c == time_col: continue
        nunique = df[c].nunique(dropna=False)
        if 1 < nunique < n * 0.2:  # 高重复率，可能需要分组
            has_groups = True
            group_cols.append(c)
    
    # 根据数据特征推荐 CV 策略
    recommended_cv = None
    if has_time:
        recommended_cv = "timeseries"
        reason = "数据包含时间列，建议使用 TimeSeriesSplit"
    elif has_groups:
        recommended_cv = "group"
        reason = f"数据包含分组结构（{group_cols}），建议使用 GroupKFold"
    else:
        recommended_cv = "kfold"
        reason = "数据无明显时间或分组结构，可使用 KFold"
    
    # 检查用户指定的 cv_type 是否合理
    if cv_type:
        if cv_type != recommended_cv:
            severity = "medium"
            if cv_type == "kfold" and has_time:
                severity = "high"  # 时间数据用 KFold 风险很高
            elif cv_type == "kfold" and has_groups:
                severity = "medium"  # 分组数据用 KFold 中等风险
            
            risks.append(RiskItem(
                name="CV strategy mismatch",
                severity=severity,
                detail=f"指定的 CV 策略（{cv_type}）可能不适合数据特征。{reason}。",
                evidence={
                    "specified": cv_type,
                    "recommended": recommended_cv,
                    "has_time": has_time,
                    "has_groups": has_groups,
                    "group_columns": group_cols
                },
            ))
    else:
        # 用户未指定，给出建议
        risks.append(RiskItem(
            name="CV strategy recommendation",
            severity="low",
            detail=f"未指定 CV 策略。{reason}。",
            evidence={
                "recommended": recommended_cv,
                "has_time": has_time,
                "has_groups": has_groups,
                "group_columns": group_cols
            },
        ))
    
    return risks

def run_checks(df: pd.DataFrame, target: str, time_col: Optional[str], cv_type: Optional[str] = None) -> Dict:
    risks = []
    risks += detect_target_leakage(df, target)
    risks += detect_target_encoding_leakage(df, target, time_col)
    risks += detect_kfold_group_leakage(df, target)
    risks += detect_time_column_issues(df, time_col)
    risks += detect_cv_consistency_issues(df, target, time_col, cv_type)
    return {"risks": [r.to_dict() for r in risks]}

