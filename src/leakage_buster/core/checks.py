
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Protocol
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import TimeSeriesSplit, KFold
import re

@dataclass
class RiskItem:
    name: str
    severity: str
    detail: str
    evidence: Dict
    leak_score: float = 0.0
    def to_dict(self): return asdict(self)

class DetectorProtocol(Protocol):
    """检测器接口协议"""
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        """检测方法，返回风险项列表"""
        ...

class BaseDetector:
    """检测器基类"""
    def __init__(self, name: str):
        self.name = name
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        """子类需要实现此方法"""
        raise NotImplementedError

class TargetLeakageDetector(BaseDetector):
    """目标泄漏检测器"""
    def __init__(self):
        super().__init__("target_leakage")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
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
                leak_score=0.9
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
                leak_score=0.7
            ))
        return risks

class StatisticalLeakageDetector(BaseDetector):
    """统计类泄漏检测器 - v0.3实装版"""
    def __init__(self):
        super().__init__("statistical_leakage")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        """检测TE/WOE/滚动统计类泄漏"""
        risks: List[RiskItem] = []
        
        # 1. 检测TE/WOE特征
        te_woe_risks = self._detect_te_woe_leakage(df, target, time_col)
        risks.extend(te_woe_risks)
        
        # 2. 检测滚动统计泄漏
        rolling_risks = self._detect_rolling_stat_leakage(df, target, time_col)
        risks.extend(rolling_risks)
        
        # 3. 检测聚合痕迹
        aggregation_risks = self._detect_aggregation_traces(df, target, time_col)
        risks.extend(aggregation_risks)
        
        return risks
    
    def _detect_te_woe_leakage(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> List[RiskItem]:
        """检测目标编码和WOE泄漏"""
        risks: List[RiskItem] = []
        y = df[target].values
        
        # 检测疑似TE/WOE特征
        te_suspects = {}
        woe_suspects = {}
        
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target in num_cols:
            num_cols.remove(target)
        if time_col and time_col in num_cols:
            num_cols.remove(time_col)
        
        for col in num_cols:
            x = df[col].values
            if np.std(x) == 0: continue
            
            # 检查列名模式
            col_lower = col.lower()
            is_te_pattern = any(pattern in col_lower for pattern in ['_te', '_target_enc', 'target_encoding'])
            is_woe_pattern = any(pattern in col_lower for pattern in ['_woe', 'woe_', 'weight_of_evidence'])
            
            # 检查值域特征
            target_mean = np.mean(y)
            is_te_like = (np.min(x) >= 0 and np.max(x) <= 1) or (abs(np.mean(x) - target_mean) < 0.1)
            is_woe_like = np.min(x) < -2 and np.max(x) > 2  # WOE通常有较大范围
            
            # 检查与目标的相关性
            try:
                corr = np.corrcoef(x, y)[0, 1]
                if not np.isfinite(corr):
                    continue
            except Exception:
                continue
            
            leak_score = 0.0
            evidence = {"correlation": float(corr), "mean": float(np.mean(x)), "target_mean": float(target_mean)}
            
            # TE特征检测
            if (is_te_pattern or is_te_like) and abs(corr) >= 0.3:
                leak_score += 0.4
                if is_te_pattern:
                    leak_score += 0.3
                if abs(corr) >= 0.7:
                    leak_score += 0.3
                
                te_suspects[col] = {**evidence, "leak_score": leak_score}
            
            # WOE特征检测
            if (is_woe_pattern or is_woe_like) and abs(corr) >= 0.3:
                leak_score += 0.4
                if is_woe_pattern:
                    leak_score += 0.3
                if abs(corr) >= 0.7:
                    leak_score += 0.3
                
                woe_suspects[col] = {**evidence, "leak_score": leak_score}
        
        # 生成风险项
        if te_suspects:
            max_score = max(item["leak_score"] for item in te_suspects.values())
            risks.append(RiskItem(
                name="Target Encoding leakage risk",
                severity="high" if max_score >= 0.7 else "medium",
                detail=f"检测到 {len(te_suspects)} 个疑似目标编码特征，与目标高相关且值域可疑。",
                evidence={"suspicious_columns": te_suspects},
                leak_score=max_score
            ))
        
        if woe_suspects:
            max_score = max(item["leak_score"] for item in woe_suspects.values())
            risks.append(RiskItem(
                name="WOE leakage risk",
                severity="high" if max_score >= 0.7 else "medium",
                detail=f"检测到 {len(woe_suspects)} 个疑似WOE特征，与目标高相关且值域可疑。",
                evidence={"suspicious_columns": woe_suspects},
                leak_score=max_score
            ))
        
        return risks
    
    def _detect_rolling_stat_leakage(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> List[RiskItem]:
        """检测滚动统计泄漏"""
        risks: List[RiskItem] = []
        
        if not time_col or time_col not in df.columns:
            return risks
        
        # 检查时间列
        try:
            t = pd.to_datetime(df[time_col], errors="coerce")
            if t.isna().any():
                return risks
        except Exception:
            return risks
        
        # 检测疑似滚动统计特征
        rolling_suspects = {}
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target in num_cols:
            num_cols.remove(target)
        if time_col in num_cols:
            num_cols.remove(time_col)
        
        for col in num_cols:
            col_lower = col.lower()
            is_rolling_pattern = any(pattern in col_lower for pattern in [
                'rolling_', '_rolling', 'rolling_', 'moving_', '_moving', 'window_', '_window'
            ])
            
            if not is_rolling_pattern:
                continue
            
            x = df[col].values
            if np.std(x) == 0: continue
            
            # 检查是否跨越未来时点（简单启发式）
            # 如果特征值在时间序列中变化过于平滑，可能使用了未来信息
            time_sorted_idx = t.argsort()
            x_sorted = x[time_sorted_idx]
            
            # 计算平滑度（相邻值的差异）
            diffs = np.abs(np.diff(x_sorted))
            smoothness = 1.0 - (np.std(diffs) / (np.mean(np.abs(x_sorted)) + 1e-8))
            
            # 检查与目标的相关性
            try:
                corr = np.corrcoef(x, y)[0, 1]
                if not np.isfinite(corr):
                    continue
            except Exception:
                continue
            
            leak_score = 0.0
            if is_rolling_pattern:
                leak_score += 0.3
            if smoothness > 0.8:  # 过于平滑
                leak_score += 0.4
            if abs(corr) >= 0.5:
                leak_score += 0.3
            
            if leak_score >= 0.5:
                rolling_suspects[col] = {
                    "correlation": float(corr),
                    "smoothness": float(smoothness),
                    "leak_score": leak_score
                }
        
        if rolling_suspects:
            max_score = max(item["leak_score"] for item in rolling_suspects.values())
            risks.append(RiskItem(
                name="Rolling statistics leakage risk",
                severity="high" if max_score >= 0.7 else "medium",
                detail=f"检测到 {len(rolling_suspects)} 个疑似滚动统计特征，可能跨越未来时点。",
                evidence={"suspicious_columns": rolling_suspects},
                leak_score=max_score
            ))
        
        return risks
    
    def _detect_aggregation_traces(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> List[RiskItem]:
        """检测聚合痕迹"""
        risks: List[RiskItem] = []
        
        # 检测疑似聚合统计特征
        agg_suspects = {}
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target in num_cols:
            num_cols.remove(target)
        if time_col and time_col in num_cols:
            num_cols.remove(time_col)
        
        for col in num_cols:
            col_lower = col.lower()
            is_agg_pattern = any(pattern in col_lower for pattern in [
                '_mean', '_avg', '_std', '_max', '_min', '_sum', '_count', '_median',
                'mean_', 'avg_', 'std_', 'max_', 'min_', 'sum_', 'count_', 'median_'
            ])
            
            if not is_agg_pattern:
                continue
            
            x = df[col].values
            if np.std(x) == 0: continue
            
            # 检查变异系数（聚合统计通常变异较小）
            cv = np.std(x) / (np.mean(x) + 1e-8)
            
            # 检查与目标的相关性
            try:
                corr = np.corrcoef(x, y)[0, 1]
                if not np.isfinite(corr):
                    continue
            except Exception:
                continue
            
            leak_score = 0.0
            if is_agg_pattern:
                leak_score += 0.3
            if cv < 0.1:  # 变异系数很小
                leak_score += 0.4
            if abs(corr) >= 0.3:
                leak_score += 0.3
            
            if leak_score >= 0.5:
                agg_suspects[col] = {
                    "correlation": float(corr),
                    "cv": float(cv),
                    "leak_score": leak_score
                }
        
        if agg_suspects:
            max_score = max(item["leak_score"] for item in agg_suspects.values())
            risks.append(RiskItem(
                name="Aggregation traces leakage risk",
                severity="high" if max_score >= 0.7 else "medium",
                detail=f"检测到 {len(agg_suspects)} 个疑似聚合统计特征，变异系数小且与目标相关。",
                evidence={"suspicious_columns": agg_suspects},
                leak_score=max_score
            ))
        
        return risks

class KFoldGroupLeakageDetector(BaseDetector):
    """KFold分组泄漏检测器"""
    def __init__(self):
        super().__init__("kfold_group_leakage")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
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
                leak_score=0.6
            ))
        return risks

class TimeColumnIssuesDetector(BaseDetector):
    """时间列问题检测器"""
    def __init__(self):
        super().__init__("time_column_issues")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        risks: List[RiskItem] = []
        if not time_col: return risks
        if time_col not in df.columns:
            risks.append(RiskItem("Time column missing", "high", f"时间列 `{time_col}` 不存在。", {}, 0.9))
            return risks
        t = pd.to_datetime(df[time_col], errors="coerce")
        miss = int(t.isna().sum())
        if miss > 0:
            risks.append(RiskItem("Time parse errors", "medium", f"`{time_col}` 有 {miss} 个无效值。", {"invalid": miss}, 0.7))
        if t.notna().any():
            risks.append(RiskItem("Time-awareness suggestion", "low",
                                  "建议使用时间感知切分/编码并校验口径一致。",
                                  {"min": str(t.min()), "max": str(t.max())}, 0.3))
        return risks

class CVConsistencyDetector(BaseDetector):
    """CV一致性检测器"""
    def __init__(self):
        super().__init__("cv_consistency")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        risks: List[RiskItem] = []
        cv_type = kwargs.get('cv_type')
        
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
                    leak_score=0.8 if severity == "high" else 0.6
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
                leak_score=0.3
            ))
        
        return risks

class DetectorRegistry:
    """检测器注册表"""
    def __init__(self):
        self.detectors: List[BaseDetector] = [
            TargetLeakageDetector(),
            StatisticalLeakageDetector(),  # v0.3实装版
            KFoldGroupLeakageDetector(),
            TimeColumnIssuesDetector(),
            CVConsistencyDetector(),
        ]
    
    def run_all_detectors(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> Dict:
        """运行所有检测器"""
        all_risks = []
        for detector in self.detectors:
            try:
                risks = detector.detect(df, target, time_col, **kwargs)
                all_risks.extend(risks)
            except Exception as e:
                # 检测器出错时记录但不中断
                all_risks.append(RiskItem(
                    name=f"Detector error: {detector.name}",
                    severity="low",
                    detail=f"检测器 {detector.name} 执行出错: {str(e)}",
                    evidence={"error": str(e)},
                    leak_score=0.0
                ))
        
        return {"risks": [r.to_dict() for r in all_risks]}

# 保持向后兼容的接口
def run_checks(df: pd.DataFrame, target: str, time_col: Optional[str] = None, cv_type: Optional[str] = None) -> Dict:
    """向后兼容的检测接口"""
    registry = DetectorRegistry()
    return registry.run_all_detectors(df, target, time_col, cv_type=cv_type)

