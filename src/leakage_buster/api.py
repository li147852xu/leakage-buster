
from __future__ import annotations
import pandas as pd
from typing import Dict, Optional, Any
from .core.checks import run_checks
from .core.fix_plan import create_fix_plan, FixPlan
from .core.fix_apply import apply_fixes, get_fix_summary, validate_fix_plan
from .core.cv_policy import audit_cv_policy
from .core.simulator import run_time_series_simulation
from .core.export import export_report

class AuditResult:
    """审计结果类"""
    
    def __init__(self, data: Dict, meta: Dict):
        self.data = data
        self.meta = meta
        self.risks = data.get("risks", [])
        self.simulation = data.get("simulation")
        self.policy_audit = data.get("policy_audit")
    
    @property
    def has_high_risk(self) -> bool:
        """是否有高危风险"""
        return any(risk.get("severity") == "high" for risk in self.risks)
    
    @property
    def has_medium_risk(self) -> bool:
        """是否有中危风险"""
        return any(risk.get("severity") == "medium" for risk in self.risks)
    
    @property
    def risk_count(self) -> int:
        """风险总数"""
        return len(self.risks)
    
    @property
    def high_risk_count(self) -> int:
        """高危风险数"""
        return sum(1 for risk in self.risks if risk.get("severity") == "high")
    
    @property
    def medium_risk_count(self) -> int:
        """中危风险数"""
        return sum(1 for risk in self.risks if risk.get("severity") == "medium")
    
    @property
    def low_risk_count(self) -> int:
        """低危风险数"""
        return sum(1 for risk in self.risks if risk.get("severity") == "low")
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "data": self.data,
            "meta": self.meta,
            "summary": {
                "total_risks": self.risk_count,
                "high_risks": self.high_risk_count,
                "medium_risks": self.medium_risk_count,
                "low_risks": self.low_risk_count,
                "has_high_risk": self.has_high_risk,
                "has_medium_risk": self.has_medium_risk
            }
        }

def audit(df: pd.DataFrame, target: str, time_col: Optional[str] = None, 
          cv_type: Optional[str] = None, simulate_cv: Optional[str] = None,
          leak_threshold: float = 0.02, cv_policy_file: Optional[str] = None,
          **opts) -> AuditResult:
    """
    审计数据框的泄漏风险
    
    Args:
        df: 数据框
        target: 目标列名
        time_col: 时间列名（可选）
        cv_type: CV策略类型（可选）
        simulate_cv: 是否启用时序模拟（可选）
        leak_threshold: 泄漏阈值（默认0.02）
        cv_policy_file: CV策略文件路径（可选）
        **opts: 其他选项
    
    Returns:
        AuditResult: 审计结果
    """
    # 运行基础检测
    results = run_checks(df, target=target, time_col=time_col, cv_type=cv_type)
    
    # 运行时序模拟（如果启用）
    simulation_results = None
    if simulate_cv == "time":
        suspicious_cols = []
        for risk in results.get("risks", []):
            if "suspicious_columns" in risk.get("evidence", {}):
                suspicious_cols.extend(risk["evidence"]["suspicious_columns"].keys())
        
        if suspicious_cols:
            simulation_results = run_time_series_simulation(
                df, target, time_col, suspicious_cols, leak_threshold
            )
    
    # 运行CV策略审计（如果提供策略文件）
    policy_audit = None
    if cv_policy_file:
        policy_audit = audit_cv_policy(df, target, time_col, cv_policy_file)
    
    # 准备元数据
    meta = {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "target": target,
        "time_col": time_col,
        "cv_type": cv_type,
        "simulate_cv": simulate_cv,
        "leak_threshold": leak_threshold,
        "cv_policy_file": cv_policy_file,
        **opts
    }
    
    # 构建结果数据
    data = {
        "risks": results["risks"],
        "simulation": simulation_results,
        "policy_audit": policy_audit
    }
    
    return AuditResult(data, meta)

def plan_fixes(audit_result: AuditResult, source_file: str = "data.csv") -> FixPlan:
    """
    基于审计结果创建修复计划
    
    Args:
        audit_result: 审计结果
        source_file: 源文件名
    
    Returns:
        FixPlan: 修复计划
    """
    return create_fix_plan(
        audit_result.risks,
        source_file,
        audit_result.meta["target"],
        audit_result.meta.get("time_col")
    )

def apply_fixes_to_dataframe(df: pd.DataFrame, fix_plan: FixPlan) -> pd.DataFrame:
    """
    应用修复计划到数据框
    
    Args:
        df: 数据框
        fix_plan: 修复计划
    
    Returns:
        pd.DataFrame: 修复后的数据框
    """
    return apply_fixes(
        df,
        fix_plan,
        fix_plan.target_column,
        fix_plan.time_column
    )

def export_audit_result(audit_result: AuditResult, output_dir: str, 
                       export_pdf: bool = False, export_sarif: bool = False) -> Dict:
    """
    导出审计结果
    
    Args:
        audit_result: 审计结果
        output_dir: 输出目录
        export_pdf: 是否导出PDF
        export_sarif: 是否导出SARIF
    
    Returns:
        Dict: 导出结果
    """
    import os
    from .core.report import render_report, write_meta
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成HTML报告
    report_path = render_report(
        audit_result.data,
        audit_result.meta,
        output_dir,
        audit_result.simulation,
        audit_result.policy_audit
    )
    
    # 写入元数据
    meta_path = os.path.join(output_dir, "meta.json")
    write_meta(audit_result.meta, output_dir)
    
    result = {
        "report": report_path,
        "meta": meta_path,
        "exports": {}
    }
    
    # PDF导出
    if export_pdf:
        pdf_path = os.path.join(output_dir, "report.pdf")
        pdf_result = export_report(report_path, pdf_path, "pdf")
        result["exports"]["pdf"] = pdf_result
    
    # SARIF导出
    if export_sarif:
        sarif_path = os.path.join(output_dir, "leakage.sarif")
        sarif_result = export_report(None, sarif_path, "sarif", audit_result.data)
        result["exports"]["sarif"] = sarif_result
    
    return result

# 便捷函数
def quick_audit(df: pd.DataFrame, target: str, **kwargs) -> AuditResult:
    """快速审计"""
    return audit(df, target, **kwargs)

def quick_fix(df: pd.DataFrame, target: str, **kwargs) -> tuple[pd.DataFrame, FixPlan]:
    """快速修复"""
    audit_result = audit(df, target, **kwargs)
    fix_plan = plan_fixes(audit_result)
    fixed_df = apply_fixes_to_dataframe(df, fix_plan)
    return fixed_df, fix_plan

