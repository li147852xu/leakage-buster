
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .fix_plan import FixPlan, FixAction

def apply_fixes(df: pd.DataFrame, fix_plan: FixPlan, target: str, time_col: Optional[str] = None) -> pd.DataFrame:
    """应用修复计划到数据框"""
    df_fixed = df.copy()
    
    # 记录修复操作
    applied_fixes = []
    
    # 1. 删除高危泄漏列
    for item in fix_plan.delete_columns:
        if item.column in df_fixed.columns:
            df_fixed = df_fixed.drop(columns=[item.column])
            applied_fixes.append({
                "action": "delete",
                "column": item.column,
                "reason": item.reason,
                "confidence": item.confidence
            })
    
    # 2. 重算目标编码特征（示例实现）
    for item in fix_plan.recalculate_columns:
        if item.column in df_fixed.columns:
            # 这里只是示例，实际应该根据具体特征类型重算
            if "target_enc" in item.column.lower() or "te_" in item.column.lower():
                # 示例：简单的目标编码重算（实际应该用CV内数据）
                df_fixed[item.column] = _recalculate_target_encoding(
                    df_fixed, item.column, target, time_col
                )
                applied_fixes.append({
                    "action": "recalculate",
                    "column": item.column,
                    "reason": item.reason,
                    "confidence": item.confidence
                })
            elif "rolling" in item.column.lower() or "moving" in item.column.lower():
                # 示例：滚动统计重算（仅使用历史数据）
                df_fixed[item.column] = _recalculate_rolling_stats(
                    df_fixed, item.column, time_col
                )
                applied_fixes.append({
                    "action": "recalculate",
                    "column": item.column,
                    "reason": item.reason,
                    "confidence": item.confidence
                })
    
    # 3. 添加修复元数据
    df_fixed.attrs['leakage_buster_fixes'] = applied_fixes
    df_fixed.attrs['leakage_buster_plan'] = fix_plan.model_dump()
    
    return df_fixed

def _recalculate_target_encoding(df: pd.DataFrame, col: str, target: str, time_col: Optional[str] = None) -> pd.Series:
    """重算目标编码（示例实现）"""
    # 这是一个简化的示例，实际应该使用CV内数据
    if time_col and time_col in df.columns:
        # 时间感知的目标编码
        df_sorted = df.sort_values(time_col)
        result = df_sorted.groupby(col)[target].transform('mean')
    else:
        # 简单的目标编码
        result = df.groupby(col)[target].transform('mean')
    
    return result

def _recalculate_rolling_stats(df: pd.DataFrame, col: str, time_col: Optional[str] = None) -> pd.Series:
    """重算滚动统计（示例实现）"""
    if time_col and time_col in df.columns:
        # 时间感知的滚动统计
        df_sorted = df.sort_values(time_col)
        if "avg" in col.lower() or "mean" in col.lower():
            # 滚动平均
            base_col = col.replace("rolling_", "").replace("_avg", "").replace("_mean", "")
            if base_col in df_sorted.columns:
                result = df_sorted[base_col].rolling(window=7, min_periods=1).mean()
            else:
                result = df_sorted[col]  # 保持原值
        else:
            result = df_sorted[col]  # 保持原值
    else:
        result = df[col]  # 保持原值
    
    return result

def get_fix_summary(fix_plan: FixPlan) -> Dict:
    """获取修复摘要"""
    return {
        "total_risks": fix_plan.total_risks,
        "high_risk_items": fix_plan.high_risk_items,
        "medium_risk_items": fix_plan.medium_risk_items,
        "low_risk_items": fix_plan.low_risk_items,
        "delete_columns": len(fix_plan.delete_columns),
        "recalculate_columns": len(fix_plan.recalculate_columns),
        "cv_recommendations": len(fix_plan.cv_recommendations),
        "group_recommendations": len(fix_plan.group_recommendations),
        "created_at": fix_plan.created_at
    }

def validate_fix_plan(fix_plan: FixPlan) -> Dict:
    """验证修复计划"""
    issues = []
    
    # 检查是否有高危项目
    if fix_plan.high_risk_items > 0:
        issues.append(f"发现 {fix_plan.high_risk_items} 个高危风险项")
    
    # 检查删除列是否合理
    if len(fix_plan.delete_columns) > 0:
        issues.append(f"将删除 {len(fix_plan.delete_columns)} 个列")
    
    # 检查重算列是否合理
    if len(fix_plan.recalculate_columns) > 0:
        issues.append(f"将重算 {len(fix_plan.recalculate_columns)} 个列")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": issues if issues else []
    }

