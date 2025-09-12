
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit, KFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import warnings

class TimeSeriesSimulator:
    """时序模拟器 - 对比TimeSeriesSplit与KFold的OOF指标"""
    
    def __init__(self, n_splits: int = 5, random_state: int = 42):
        self.n_splits = n_splits
        self.random_state = random_state
        self.results = {}
    
    def compare_cv_strategies(self, 
                            df: pd.DataFrame, 
                            target: str, 
                            time_col: Optional[str] = None,
                            suspicious_cols: List[str] = None,
                            leak_threshold: float = 0.02) -> Dict:
        """
        对比TimeSeriesSplit与KFold的OOF指标
        
        Args:
            df: 数据框
            target: 目标列名
            time_col: 时间列名
            suspicious_cols: 可疑特征列名列表
            leak_threshold: 泄漏阈值
            
        Returns:
            对比结果字典
        """
        if suspicious_cols is None:
            suspicious_cols = []
        
        if not suspicious_cols:
            return {"message": "没有可疑特征需要对比", "comparisons": []}
        
        # 准备数据
        X = df[suspicious_cols].values
        y = df[target].values
        
        # 确保数据没有缺失值
        valid_mask = ~(np.isnan(X).any(axis=1) | np.isnan(y))
        X = X[valid_mask]
        y = y[valid_mask]
        
        if len(X) < 10:  # 数据太少
            return {"message": "数据量不足，无法进行对比", "comparisons": []}
        
        comparisons = []
        
        for col in suspicious_cols:
            try:
                comparison = self._compare_single_feature(
                    df[col].values[valid_mask], y, time_col, col, leak_threshold
                )
                if comparison:
                    comparisons.append(comparison)
            except Exception as e:
                warnings.warn(f"对比特征 {col} 时出错: {str(e)}")
                continue
        
        return {
            "message": f"对比了 {len(comparisons)} 个可疑特征",
            "comparisons": comparisons,
            "leak_threshold": leak_threshold
        }
    
    def _compare_single_feature(self, 
                              feature: np.ndarray, 
                              target: np.ndarray, 
                              time_col: Optional[str],
                              feature_name: str,
                              leak_threshold: float) -> Optional[Dict]:
        """对比单个特征的CV策略"""
        
        # 检查特征是否有效
        if np.std(feature) == 0 or len(np.unique(target)) < 2:
            return None
        
        # 准备数据
        X = feature.reshape(-1, 1)
        y = target
        
        # TimeSeriesSplit结果
        ts_scores = self._get_cv_scores(X, y, TimeSeriesSplit(n_splits=self.n_splits))
        
        # KFold结果
        kf_scores = self._get_cv_scores(X, y, KFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state))
        
        if not ts_scores or not kf_scores:
            return None
        
        # 计算差异
        ts_mean = np.mean(ts_scores)
        kf_mean = np.mean(kf_scores)
        score_diff = kf_mean - ts_mean
        
        # 判断是否泄漏
        is_leak = abs(score_diff) > leak_threshold
        
        return {
            "feature": feature_name,
            "timeseries_cv": {
                "scores": ts_scores,
                "mean": float(ts_mean),
                "std": float(np.std(ts_scores))
            },
            "kfold_cv": {
                "scores": kf_scores,
                "mean": float(kf_mean),
                "std": float(np.std(kf_scores))
            },
            "score_difference": float(score_diff),
            "is_leak": is_leak,
            "leak_severity": self._get_leak_severity(abs(score_diff), leak_threshold)
        }
    
    def _get_cv_scores(self, X: np.ndarray, y: np.ndarray, cv_splitter) -> List[float]:
        """获取CV分数"""
        scores = []
        
        for train_idx, val_idx in cv_splitter.split(X):
            try:
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]
                
                # 检查训练集和验证集是否有效
                if len(np.unique(y_train)) < 2 or len(np.unique(y_val)) < 2:
                    continue
                
                # 训练模型
                model = LogisticRegression(random_state=self.random_state, max_iter=1000)
                model.fit(X_train, y_train)
                
                # 预测并计算AUC
                y_pred = model.predict_proba(X_val)[:, 1]
                auc = roc_auc_score(y_val, y_pred)
                
                if np.isfinite(auc):
                    scores.append(auc)
                    
            except Exception as e:
                warnings.warn(f"CV fold计算出错: {str(e)}")
                continue
        
        return scores
    
    def _get_leak_severity(self, score_diff: float, threshold: float) -> str:
        """根据分数差异确定泄漏严重程度"""
        if score_diff > threshold * 3:
            return "high"
        elif score_diff > threshold * 2:
            return "medium"
        elif score_diff > threshold:
            return "low"
        else:
            return "none"
    
    def generate_summary(self, comparison_results: Dict) -> Dict:
        """生成对比摘要"""
        comparisons = comparison_results.get("comparisons", [])
        
        if not comparisons:
            return {"summary": "没有可对比的特征", "leak_count": 0}
        
        leak_features = [comp for comp in comparisons if comp.get("is_leak", False)]
        high_leak_features = [comp for comp in leak_features 
                            if comp.get("leak_severity") == "high"]
        
        return {
            "total_features": len(comparisons),
            "leak_features": len(leak_features),
            "high_leak_features": len(high_leak_features),
            "leak_rate": len(leak_features) / len(comparisons) if comparisons else 0,
            "avg_score_diff": np.mean([comp.get("score_difference", 0) for comp in comparisons]),
            "max_score_diff": max([abs(comp.get("score_difference", 0)) for comp in comparisons]) if comparisons else 0
        }

def run_time_series_simulation(df: pd.DataFrame, 
                              target: str, 
                              time_col: Optional[str] = None,
                              suspicious_cols: List[str] = None,
                              leak_threshold: float = 0.02,
                              n_splits: int = 5) -> Dict:
    """
    运行时序模拟对比
    
    Args:
        df: 数据框
        target: 目标列名
        time_col: 时间列名
        suspicious_cols: 可疑特征列名列表
        leak_threshold: 泄漏阈值
        n_splits: CV折数
        
    Returns:
        模拟结果
    """
    simulator = TimeSeriesSimulator(n_splits=n_splits)
    
    # 运行对比
    comparison_results = simulator.compare_cv_strategies(
        df, target, time_col, suspicious_cols, leak_threshold
    )
    
    # 生成摘要
    summary = simulator.generate_summary(comparison_results)
    
    return {
        "simulation_results": comparison_results,
        "summary": summary,
        "parameters": {
            "leak_threshold": leak_threshold,
            "n_splits": n_splits,
            "time_col": time_col
        }
    }

