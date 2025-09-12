
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Protocol
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

class TargetEncodingLeakageDetector(BaseDetector):
    """目标编码泄漏检测器"""
    def __init__(self):
        super().__init__("target_encoding_leakage")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
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

class StatisticalLeakageDetector(BaseDetector):
    """统计类泄漏检测器（预览版）"""
    def __init__(self):
        super().__init__("statistical_leakage")
    
    def detect(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None, **kwargs) -> List[RiskItem]:
        """统计类泄漏检测（占位实现）"""
        risks: List[RiskItem] = []
        
        # 占位实现：检测可能的统计特征
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if target in num_cols:
            num_cols.remove(target)
        if time_col and time_col in num_cols:
            num_cols.remove(time_col)
        
        # 检测疑似统计特征（变异系数较小，可能是聚合统计）
        stat_suspects = {}
        for c in num_cols:
            x = df[c].values
            if np.std(x) == 0: continue
            
            # 计算变异系数
            cv = np.std(x) / (np.mean(x) + 1e-8)
            if cv < 0.05:  # 变异系数很小，疑似统计特征
                try:
                    corr = np.corrcoef(x, df[target].values)[0, 1]
                    if np.isfinite(corr) and abs(corr) >= 0.1:
                        stat_suspects[c] = {"cv": float(cv), "corr": float(corr)}
                except Exception:
                    continue
        
        if stat_suspects:
            risks.append(RiskItem(
                name="Statistical leakage (preview)",
                severity="medium",
                detail="以下列疑似统计特征，需要确认是否在CV内正确计算。",
                evidence={"columns": stat_suspects, "note": "这是预览版检测，具体实现待完善"},
            ))
        
        return risks

class DetectorRegistry:
    """检测器注册表"""
    def __init__(self):
        self.detectors: List[BaseDetector] = [
            TargetLeakageDetector(),
            TargetEncodingLeakageDetector(),
            KFoldGroupLeakageDetector(),
            TimeColumnIssuesDetector(),
            CVConsistencyDetector(),
            StatisticalLeakageDetector(),  # 新增统计类泄漏检测器
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
                    evidence={"error": str(e)}
                ))
        
        return {"risks": [r.to_dict() for r in all_risks]}

# 保持向后兼容的接口
def run_checks(df: pd.DataFrame, target: str, time_col: Optional[str] = None, cv_type: Optional[str] = None) -> Dict:
    """向后兼容的检测接口"""
    registry = DetectorRegistry()
    return registry.run_all_detectors(df, target, time_col, cv_type=cv_type)

# 新增统计类泄漏检测接口（占位）
def stat_leak_skeleton(df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> Dict:
    """统计类泄漏检测骨架（占位实现）"""
    detector = StatisticalLeakageDetector()
    risks = detector.detect(df, target, time_col)
    return {"risks": [r.to_dict() for r in risks]}

