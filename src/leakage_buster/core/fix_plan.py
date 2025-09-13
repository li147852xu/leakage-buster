
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class FixAction(str, Enum):
    """修复动作类型"""
    DELETE = "delete"
    RECALCULATE = "recalculate"
    RECOMMEND_CV = "recommend_cv"
    RECOMMEND_GROUPS = "recommend_groups"

class FixItem(BaseModel):
    """单个修复项"""
    action: FixAction
    column: str
    reason: str
    evidence: Dict[str, Any]
    risk_source: str  # 来源风险项名称
    severity: str  # high, medium, low
    confidence: float = Field(ge=0.0, le=1.0)  # 置信度
    details: Optional[str] = None

class FixPlan(BaseModel):
    """修复计划"""
    version: str = "1.0"
    total_risks: int
    high_risk_items: int
    medium_risk_items: int
    low_risk_items: int
    
    # 修复项列表
    delete_columns: List[FixItem] = Field(default_factory=list)
    recalculate_columns: List[FixItem] = Field(default_factory=list)
    cv_recommendations: List[FixItem] = Field(default_factory=list)
    group_recommendations: List[FixItem] = Field(default_factory=list)
    
    # 元数据
    created_at: str
    source_file: str
    target_column: str
    time_column: Optional[str] = None
    
    class Config:
        json_encoders = {
            # 自定义JSON编码器
        }

def create_fix_plan(risks: List[Dict], source_file: str, target: str, time_col: Optional[str] = None) -> FixPlan:
    """从风险列表创建修复计划"""
    import datetime
    
    delete_items = []
    recalculate_items = []
    cv_items = []
    group_items = []
    
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for risk in risks:
        risk_name = risk.get("name", "")
        severity = risk.get("severity", "low")
        evidence = risk.get("evidence", {})
        
        if severity == "high":
            high_count += 1
        elif severity == "medium":
            medium_count += 1
        else:
            low_count += 1
        
        # 根据风险类型创建修复项
        if "Target leakage (high correlation)" in risk_name:
            # 删除高相关列
            columns = list(evidence.get("columns", {}).keys())
            for col in columns:
                delete_items.append(FixItem(
                    action=FixAction.DELETE,
                    column=col,
                    reason=f"高相关性泄漏：与目标相关性过高",
                    evidence=evidence,
                    risk_source=risk_name,
                    severity=severity,
                    confidence=0.9,
                    details=f"相关性: {evidence.get('columns', {}).get(col, 'N/A')}"
                ))
        
        elif "Target encoding leakage" in risk_name:
            # 重算目标编码
            columns = list(evidence.get("suspicious_columns", {}).keys())
            for col in columns:
                recalculate_items.append(FixItem(
                    action=FixAction.RECALCULATE,
                    column=col,
                    reason=f"目标编码泄漏：疑似使用全量数据计算",
                    evidence=evidence,
                    risk_source=risk_name,
                    severity=severity,
                    confidence=0.8,
                    details=f"建议在CV内重新计算目标编码"
                ))
        
        elif "Rolling statistics leakage" in risk_name:
            # 重算滚动统计
            columns = list(evidence.get("suspicious_columns", {}).keys())
            for col in columns:
                recalculate_items.append(FixItem(
                    action=FixAction.RECALCULATE,
                    column=col,
                    reason=f"滚动统计泄漏：疑似使用未来信息",
                    evidence=evidence,
                    risk_source=risk_name,
                    severity=severity,
                    confidence=0.85,
                    details=f"建议仅使用历史窗口数据重新计算"
                ))
        
        elif "KFold leakage risk" in risk_name:
            # 推荐GroupKFold
            candidates = evidence.get("candidates", [])
            for candidate in candidates:
                group_items.append(FixItem(
                    action=FixAction.RECOMMEND_GROUPS,
                    column=candidate.get("column", ""),
                    reason=f"分组泄漏风险：高重复率列",
                    evidence=evidence,
                    risk_source=risk_name,
                    severity=severity,
                    confidence=0.7,
                    details=f"重复率: {candidate.get('dup_rate', 'N/A')}"
                ))
        
        elif "CV strategy recommendation" in risk_name:
            # 推荐CV策略
            recommended = evidence.get("recommended", "")
            cv_items.append(FixItem(
                action=FixAction.RECOMMEND_CV,
                column="",
                reason=f"CV策略推荐：{recommended}",
                evidence=evidence,
                risk_source=risk_name,
                severity=severity,
                confidence=0.6,
                details=f"数据特征: 时间列={evidence.get('has_time', False)}, 分组={evidence.get('has_groups', False)}"
            ))
    
    return FixPlan(
        total_risks=len(risks),
        high_risk_items=high_count,
        medium_risk_items=medium_count,
        low_risk_items=low_count,
        delete_columns=delete_items,
        recalculate_columns=recalculate_items,
        cv_recommendations=cv_items,
        group_recommendations=group_items,
        created_at=datetime.datetime.now().isoformat(),
        source_file=source_file,
        target_column=target,
        time_column=time_col
    )

