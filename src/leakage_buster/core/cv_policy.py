
from __future__ import annotations
import yaml
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import pandas as pd

@dataclass
class CVPolicy:
    """CV策略配置"""
    cv_type: str  # kfold, timeseries, group
    n_splits: int = 5
    time_col: Optional[str] = None
    group_cols: List[str] = None
    sampling_strategy: Optional[str] = None  # random, stratified, time_aware
    random_state: int = 42
    
    def __post_init__(self):
        if self.group_cols is None:
            self.group_cols = []

@dataclass
class PolicyViolation:
    """策略违规项"""
    violation_type: str
    severity: str  # high, medium, low
    message: str
    expected: Any
    actual: Any
    recommendation: str

class CVPolicyAuditor:
    """CV策略审计器"""
    
    def __init__(self, policy_file: Optional[str] = None):
        self.policy_file = policy_file
        self.policy: Optional[CVPolicy] = None
        self.violations: List[PolicyViolation] = []
    
    def load_policy(self, policy_file: Optional[str] = None) -> bool:
        """加载CV策略文件"""
        if policy_file:
            self.policy_file = policy_file
        
        if not self.policy_file or not os.path.exists(self.policy_file):
            return False
        
        try:
            with open(self.policy_file, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            self.policy = CVPolicy(
                cv_type=policy_data.get('cv_type', 'kfold'),
                n_splits=policy_data.get('n_splits', 5),
                time_col=policy_data.get('time_col'),
                group_cols=policy_data.get('group_cols', []),
                sampling_strategy=policy_data.get('sampling_strategy'),
                random_state=policy_data.get('random_state', 42)
            )
            return True
        except Exception as e:
            print(f"Error loading policy file: {e}")
            return False
    
    def audit_data(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None) -> Dict:
        """审计数据是否符合策略"""
        self.violations = []
        
        if not self.policy:
            return {
                "status": "no_policy",
                "message": "No policy file loaded",
                "violations": []
            }
        
        # 1. 检查CV类型匹配
        self._check_cv_type_match(df, target, time_col)
        
        # 2. 检查时间列配置
        self._check_time_column_config(time_col)
        
        # 3. 检查分组列配置
        self._check_group_columns_config(df)
        
        # 4. 检查数据特征
        self._check_data_characteristics(df, target, time_col)
        
        # 5. 检查采样策略
        self._check_sampling_strategy(df, target)
        
        return {
            "status": "audited",
            "policy_file": self.policy_file,
            "violations": [self._violation_to_dict(v) for v in self.violations],
            "summary": self._generate_summary()
        }
    
    def _check_cv_type_match(self, df: pd.DataFrame, target: str, time_col: Optional[str] = None):
        """检查CV类型是否匹配数据特征"""
        has_time = time_col and time_col in df.columns
        has_groups = self._has_group_structure(df, target, time_col)
        
        expected_cv = self.policy.cv_type
        recommended_cv = self._recommend_cv_type(has_time, has_groups)
        
        if expected_cv != recommended_cv:
            severity = "high" if self._is_critical_mismatch(expected_cv, has_time, has_groups) else "medium"
            
            self.violations.append(PolicyViolation(
                violation_type="cv_type_mismatch",
                severity=severity,
                message=f"CV类型不匹配：策略指定{expected_cv}，但数据特征建议{recommended_cv}",
                expected=recommended_cv,
                actual=expected_cv,
                recommendation=f"建议将CV类型改为{recommended_cv}以匹配数据特征"
            ))
    
    def _check_time_column_config(self, time_col: Optional[str]):
        """检查时间列配置"""
        expected_time_col = self.policy.time_col
        
        if expected_time_col and not time_col:
            self.violations.append(PolicyViolation(
                violation_type="missing_time_column",
                severity="high",
                message="策略要求时间列但数据中未提供",
                expected=expected_time_col,
                actual=None,
                recommendation="请提供时间列或更新策略配置"
            ))
        elif time_col and expected_time_col and time_col != expected_time_col:
            self.violations.append(PolicyViolation(
                violation_type="time_column_mismatch",
                severity="medium",
                message=f"时间列不匹配：策略要求{expected_time_col}，实际使用{time_col}",
                expected=expected_time_col,
                actual=time_col,
                recommendation="请使用策略指定的时间列或更新策略配置"
            ))
    
    def _check_group_columns_config(self, df: pd.DataFrame):
        """检查分组列配置"""
        expected_group_cols = set(self.policy.group_cols)
        actual_group_cols = set(df.columns)
        
        missing_cols = expected_group_cols - actual_group_cols
        if missing_cols:
            self.violations.append(PolicyViolation(
                violation_type="missing_group_columns",
                severity="high",
                message=f"策略要求的分组列在数据中缺失：{list(missing_cols)}",
                expected=list(expected_group_cols),
                actual=list(actual_group_cols),
                recommendation="请确保数据包含所有策略要求的分组列"
            ))
        
        # 检查是否有额外的分组列
        extra_cols = actual_group_cols - expected_group_cols
        if extra_cols and self.policy.cv_type == "group":
            self.violations.append(PolicyViolation(
                violation_type="extra_group_columns",
                severity="low",
                message=f"数据中有额外的分组列：{list(extra_cols)}",
                expected=list(expected_group_cols),
                actual=list(actual_group_cols),
                recommendation="考虑将额外分组列加入策略配置"
            ))
    
    def _check_data_characteristics(self, df: pd.DataFrame, target: str, time_col: Optional[str]):
        """检查数据特征"""
        n_rows = len(df)
        n_cols = len(df.columns)
        
        # 检查数据量是否足够
        if n_rows < self.policy.n_splits * 2:
            self.violations.append(PolicyViolation(
                violation_type="insufficient_data",
                severity="high",
                message=f"数据量不足：{n_rows}行，CV需要至少{self.policy.n_splits * 2}行",
                expected=self.policy.n_splits * 2,
                actual=n_rows,
                recommendation="增加数据量或减少CV折数"
            ))
        
        # 检查时间列数据质量
        if time_col and time_col in df.columns:
            time_series = pd.to_datetime(df[time_col], errors='coerce')
            invalid_count = time_series.isna().sum()
            if invalid_count > 0:
                self.violations.append(PolicyViolation(
                    violation_type="invalid_time_data",
                    severity="medium",
                    message=f"时间列有{invalid_count}个无效值",
                    expected=0,
                    actual=invalid_count,
                    recommendation="清理时间列数据或处理无效值"
                ))
    
    def _check_sampling_strategy(self, df: pd.DataFrame, target: str):
        """检查采样策略"""
        if not self.policy.sampling_strategy:
            return
        
        strategy = self.policy.sampling_strategy
        target_values = df[target].value_counts()
        
        if strategy == "stratified" and len(target_values) < 2:
            self.violations.append(PolicyViolation(
                violation_type="invalid_sampling_strategy",
                severity="medium",
                message="策略要求分层采样但目标只有单一类别",
                expected="多类别目标",
                actual="单类别目标",
                recommendation="更改采样策略或确保目标有多类别"
            ))
        
        elif strategy == "time_aware" and not self.policy.time_col:
            self.violations.append(PolicyViolation(
                violation_type="invalid_sampling_strategy",
                severity="high",
                message="策略要求时间感知采样但未配置时间列",
                expected="时间列配置",
                actual="无时间列",
                recommendation="配置时间列或更改采样策略"
            ))
    
    def _has_group_structure(self, df: pd.DataFrame, target: str, time_col: Optional[str]) -> bool:
        """检查是否有分组结构"""
        n = len(df)
        for col in df.columns:
            if col == target or col == time_col:
                continue
            nunique = df[col].nunique(dropna=False)
            if 1 < nunique < n * 0.2:  # 高重复率
                return True
        return False
    
    def _recommend_cv_type(self, has_time: bool, has_groups: bool) -> str:
        """推荐CV类型"""
        if has_time:
            return "timeseries"
        elif has_groups:
            return "group"
        else:
            return "kfold"
    
    def _is_critical_mismatch(self, cv_type: str, has_time: bool, has_groups: bool) -> bool:
        """判断是否为关键不匹配"""
        if cv_type == "kfold" and has_time:
            return True  # 时间数据用KFold是严重错误
        return False
    
    def _violation_to_dict(self, violation: PolicyViolation) -> Dict:
        """将违规项转换为字典"""
        return {
            "violation_type": violation.violation_type,
            "severity": violation.severity,
            "message": violation.message,
            "expected": violation.expected,
            "actual": violation.actual,
            "recommendation": violation.recommendation
        }
    
    def _generate_summary(self) -> Dict:
        """生成审计摘要"""
        if not self.violations:
            return {
                "total_violations": 0,
                "high_severity": 0,
                "medium_severity": 0,
                "low_severity": 0,
                "compliance_status": "compliant"
            }
        
        high_count = sum(1 for v in self.violations if v.severity == "high")
        medium_count = sum(1 for v in self.violations if v.severity == "medium")
        low_count = sum(1 for v in self.violations if v.severity == "low")
        
        compliance_status = "non_compliant" if high_count > 0 else "partially_compliant" if medium_count > 0 else "compliant"
        
        return {
            "total_violations": len(self.violations),
            "high_severity": high_count,
            "medium_severity": medium_count,
            "low_severity": low_count,
            "compliance_status": compliance_status
        }

def audit_cv_policy(df: pd.DataFrame, target: str, time_col: Optional[str] = None, 
                   policy_file: Optional[str] = None) -> Dict:
    """审计CV策略的便捷函数"""
    auditor = CVPolicyAuditor(policy_file)
    if policy_file:
        auditor.load_policy()
    return auditor.audit_data(df, target, time_col)

