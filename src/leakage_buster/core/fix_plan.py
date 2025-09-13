
from __future__ import annotations
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class FixAction(BaseModel):
    """修复动作"""
    action_type: Literal["delete", "recalculate", "recommend_cv", "recommend_groups"]
    target: str  # 目标列名或CV策略
    reason: str  # 修复原因
    evidence: Dict[str, Any]  # 证据引用
    severity: Literal["high", "medium", "low"]
    confidence: float = Field(ge=0.0, le=1.0)  # 置信度

class FixPlan(BaseModel):
    """修复计划"""
    plan_id: str
    created_at: datetime
    source_risks: List[str]  # 来源风险ID列表
    actions: List[FixAction]
    summary: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FixResult(BaseModel):
    """修复结果"""
    success: bool
    message: str
    fixed_columns: List[str]
    removed_columns: List[str]
    recommended_cv: Optional[str] = None
    recommended_groups: List[str] = []
    warnings: List[str] = []

def create_fix_plan(risks: List[Dict], plan_id: str = None) -> FixPlan:
    """从风险列表创建修复计划"""
    if plan_id is None:
        plan_id = f"fix_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    actions = []
    source_risks = []
    
    for risk in risks:
        risk_id = risk.get("name", "unknown")
        source_risks.append(risk_id)
        
        risk_name = risk["name"]
        severity = risk.get("severity", "medium")
        evidence = risk.get("evidence", {})
        
        if risk_name.startswith("Target leakage (high correlation)"):
            # 删除高相关列
            columns = list(evidence.get("columns", {}).keys())
            for col in columns:
                actions.append(FixAction(
                    action_type="delete",
                    target=col,
                    reason=f"高相关性泄漏 (corr={evidence['columns'][col]:.3f})",
                    evidence={"correlation": evidence["columns"][col]},
                    severity="high",
                    confidence=0.9
                ))
        
        elif risk_name.startswith("Target encoding leakage"):
            # 重算目标编码
            columns = list(evidence.get("suspicious_columns", {}).keys())
            for col in columns:
                actions.append(FixAction(
                    action_type="recalculate",
                    target=col,
                    reason="疑似目标编码泄漏，需要在CV内重算",
                    evidence=evidence["suspicious_columns"][col],
                    severity="high",
                    confidence=0.8
                ))
        
        elif risk_name.startswith("WOE leakage"):
            # 重算WOE
            columns = list(evidence.get("suspicious_columns", {}).keys())
            for col in columns:
                actions.append(FixAction(
                    action_type="recalculate",
                    target=col,
                    reason="疑似WOE泄漏，需要检查计算时间窗口",
                    evidence=evidence["suspicious_columns"][col],
                    severity="high",
                    confidence=0.8
                ))
        
        elif risk_name.startswith("Rolling statistics leakage"):
            # 重算滚动统计
            columns = list(evidence.get("suspicious_columns", {}).keys())
            for col in columns:
                actions.append(FixAction(
                    action_type="recalculate",
                    target=col,
                    reason="疑似滚动统计泄漏，需要确保仅使用历史窗口",
                    evidence=evidence["suspicious_columns"][col],
                    severity="high",
                    confidence=0.8
                ))
        
        elif risk_name.startswith("KFold leakage risk"):
            # 推荐GroupKFold
            candidates = evidence.get("candidates", [])
            group_cols = [c["column"] for c in candidates if c.get("dup_rate", 0) > 0.8]
            if group_cols:
                actions.append(FixAction(
                    action_type="recommend_groups",
                    target=",".join(group_cols),
                    reason=f"高重复列建议用作GroupKFold的groups",
                    evidence={"candidates": candidates},
                    severity="medium",
                    confidence=0.7
                ))
        
        elif risk_name.startswith("CV strategy recommendation"):
            # 推荐CV策略
            recommended = evidence.get("recommended", "kfold")
            actions.append(FixAction(
                action_type="recommend_cv",
                target=recommended,
                reason=f"根据数据特征推荐CV策略: {recommended}",
                evidence=evidence,
                severity="low",
                confidence=0.6
            ))
    
    # 生成摘要
    summary = {
        "total_actions": len(actions),
        "high_severity": len([a for a in actions if a.severity == "high"]),
        "medium_severity": len([a for a in actions if a.severity == "medium"]),
        "low_severity": len([a for a in actions if a.severity == "low"]),
        "delete_actions": len([a for a in actions if a.action_type == "delete"]),
        "recalculate_actions": len([a for a in actions if a.action_type == "recalculate"]),
        "recommend_actions": len([a for a in actions if a.action_type in ["recommend_cv", "recommend_groups"]])
    }
    
    return FixPlan(
        plan_id=plan_id,
        created_at=datetime.now(),
        source_risks=source_risks,
        actions=actions,
        summary=summary
    )

def save_fix_plan(plan: FixPlan, output_path: str) -> str:
    """保存修复计划到JSON文件"""
    import json
    import os
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(plan.dict(), f, ensure_ascii=False, indent=2, default=str)
    
    return output_path

def load_fix_plan(input_path: str) -> FixPlan:
    """从JSON文件加载修复计划"""
    import json
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return FixPlan(**data)

