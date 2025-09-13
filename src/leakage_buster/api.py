
from __future__ import annotations
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from .core.checks import run_checks
from .core.simulator import run_time_series_simulation
from .core.cv_policy import audit_cv_policy
from .core.fix_plan import create_fix_plan, FixPlan
from .core.fix_apply import apply_fixes, apply_minimal_fixes

@dataclass
class AuditResult:
    """审计结果"""
    risks: List[Dict[str, Any]]
    simulation: Optional[Dict[str, Any]] = None
    policy_audit: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = None
    
    def get_high_risk_count(self) -> int:
        """获取高危风险数量"""
        return len([r for r in self.risks if r.get("severity") == "high"])
    
    def get_medium_risk_count(self) -> int:
        """获取中危风险数量"""
        return len([r for r in self.risks if r.get("severity") == "medium"])
    
    def get_low_risk_count(self) -> int:
        """获取低危风险数量"""
        return len([r for r in self.risks if r.get("severity") == "low"])
    
    def has_high_risk(self) -> bool:
        """是否有高危风险"""
        return self.get_high_risk_count() > 0
    
    def get_exit_code(self) -> int:
        """获取退出码"""
        if self.has_high_risk():
            return 3  # high-leakage-found
        elif self.get_medium_risk_count() > 0:
            return 2  # warnings
        else:
            return 0  # ok

def audit(df: pd.DataFrame, target: str, time_col: Optional[str] = None, 
          cv_type: Optional[str] = None, simulate_cv: bool = False, 
          leak_threshold: float = 0.02, cv_policy_file: Optional[str] = None,
          **opts) -> AuditResult:
    """
    审计数据泄漏
    
    Args:
        df: 数据框
        target: 目标列名
        time_col: 时间列名（可选）
        cv_type: CV策略（kfold/timeseries/group）
        simulate_cv: 是否启用时序模拟
        leak_threshold: 泄漏阈值
        cv_policy_file: CV策略配置文件路径
        **opts: 其他选项
    
    Returns:
        AuditResult: 审计结果
    """
    # 运行基础检测
    results = run_checks(df, target=target, time_col=time_col, cv_type=cv_type)
    
    # 运行时序模拟（如果启用）
    simulation = None
    if simulate_cv and time_col:
        suspicious_cols = []
        for risk in results.get("risks", []):
            if "suspicious_columns" in risk.get("evidence", {}):
                suspicious_cols.extend(risk["evidence"]["suspicious_columns"].keys())
        
        if suspicious_cols:
            simulation = run_time_series_simulation(
                df, target, time_col, suspicious_cols, leak_threshold
            )
    
    # 运行CV策略审计（如果提供策略文件）
    policy_audit = None
    if cv_policy_file:
        policy_audit = audit_cv_policy(df, target, time_col, cv_policy_file)
    
    # 准备元数据
    meta = {
        "n_rows": len(df),
        "n_cols": df.shape[1],
        "target": target,
        "time_col": time_col,
        "cv_type": cv_type,
        "simulate_cv": simulate_cv,
        "leak_threshold": leak_threshold,
        "cv_policy_file": cv_policy_file
    }
    
    return AuditResult(
        risks=results.get("risks", []),
        simulation=simulation,
        policy_audit=policy_audit,
        meta=meta
    )

def plan_fixes(audit_result: AuditResult, plan_id: Optional[str] = None) -> FixPlan:
    """
    制定修复计划
    
    Args:
        audit_result: 审计结果
        plan_id: 修复计划ID（可选）
    
    Returns:
        FixPlan: 修复计划
    """
    return create_fix_plan(audit_result.risks, plan_id)

def apply_fixes(df: pd.DataFrame, fix_plan: FixPlan, target: str, 
                time_col: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    应用修复计划
    
    Args:
        df: 数据框
        fix_plan: 修复计划
        target: 目标列名
        time_col: 时间列名（可选）
    
    Returns:
        Tuple[pd.DataFrame, Dict]: 修复后的数据框和结果信息
    """
    from .core.fix_apply import apply_fixes as _apply_fixes
    
    result = _apply_fixes(df, fix_plan, target, time_col)
    
    # 应用修复
    if result.success:
        # 这里需要重新实现apply_fixes来返回修复后的数据框
        df_fixed = df.copy()
        for action in fix_plan.actions:
            if action.action_type == "delete" and action.target in df_fixed.columns:
                df_fixed = df_fixed.drop(columns=[action.target])
        
        return df_fixed, result.dict()
    else:
        return df, result.dict()

def apply_minimal_fixes(df: pd.DataFrame, audit_result: AuditResult, 
                       target: str, time_col: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    应用最小修复（仅删除高危泄漏列）
    
    Args:
        df: 数据框
        audit_result: 审计结果
        target: 目标列名
        time_col: 时间列名（可选）
    
    Returns:
        Tuple[pd.DataFrame, Dict]: 修复后的数据框和结果信息
    """
    df_fixed, result = apply_minimal_fixes(df, audit_result.risks, target, time_col)
    return df_fixed, result.dict()

# 便捷函数
def quick_audit(df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> AuditResult:
    """快速审计（仅基础检测）"""
    return audit(df, target, time_col)

def quick_fix(df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> Tuple[pd.DataFrame, AuditResult]:
    """快速修复（最小修复）"""
    audit_result = quick_audit(df, target, time_col)
    df_fixed, _ = apply_minimal_fixes(df, audit_result.risks, target, time_col)
    return df_fixed, audit_result

