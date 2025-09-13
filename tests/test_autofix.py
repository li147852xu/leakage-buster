
import pytest
import pandas as pd
import numpy as np
import os
import sys
import json
import tempfile

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from leakage_buster.api import audit, plan_fixes, apply_fixes_to_dataframe, AuditResult
from leakage_buster.core.fix_plan import FixPlan, FixAction, create_fix_plan
from leakage_buster.core.fix_apply import apply_fixes, get_fix_summary, validate_fix_plan
from leakage_buster.cli import run, EXIT_OK, EXIT_WARNINGS, EXIT_HIGH_LEAKAGE, EXIT_INVALID_CONFIG

class TestFixPlan:
    """测试修复计划"""
    
    def test_create_fix_plan(self):
        """测试创建修复计划"""
        risks = [
            {
                "name": "Target leakage (high correlation)",
                "severity": "high",
                "evidence": {
                    "columns": {"amount": 0.99}
                }
            },
            {
                "name": "Target encoding leakage risk",
                "severity": "medium",
                "evidence": {
                    "suspicious_columns": {"target_enc_feature": {"correlation": 0.85}}
                }
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target", "date")
        
        assert fix_plan.total_risks == 2
        assert fix_plan.high_risk_items == 1
        assert fix_plan.medium_risk_items == 1
        assert len(fix_plan.delete_columns) == 1
        assert len(fix_plan.recalculate_columns) == 1
        assert fix_plan.target_column == "target"
        assert fix_plan.time_column == "date"
    
    def test_fix_plan_serialization(self):
        """测试修复计划序列化"""
        risks = [
            {
                "name": "Target leakage (high correlation)",
                "severity": "high",
                "evidence": {"columns": {"amount": 0.99}}
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        plan_dict = fix_plan.model_dump()
        
        assert "version" in plan_dict
        assert "total_risks" in plan_dict
        assert "delete_columns" in plan_dict
        assert len(plan_dict["delete_columns"]) == 1
        assert plan_dict["delete_columns"][0]["action"] == "delete"
        assert plan_dict["delete_columns"][0]["column"] == "amount"

class TestFixApply:
    """测试修复应用"""
    
    def test_apply_fixes_delete(self):
        """测试删除列修复"""
        df = pd.DataFrame({
            'amount': [100, 200, 300],
            'target': [0, 1, 0],
            'keep_col': [1, 2, 3]
        })
        
        risks = [
            {
                "name": "Target leakage (high correlation)",
                "severity": "high",
                "evidence": {"columns": {"amount": 0.99}}
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        fixed_df = apply_fixes(df, fix_plan, "target")
        
        assert "amount" not in fixed_df.columns
        assert "keep_col" in fixed_df.columns
        assert "target" in fixed_df.columns
        assert len(fixed_df) == 3
    
    def test_apply_fixes_recalculate(self):
        """测试重算列修复"""
        df = pd.DataFrame({
            'target_enc_feature': [0.5, 0.6, 0.7],
            'target': [0, 1, 0],
            'group': ['A', 'A', 'B']
        })
        
        risks = [
            {
                "name": "Target encoding leakage risk",
                "severity": "medium",
                "evidence": {
                    "suspicious_columns": {"target_enc_feature": {"correlation": 0.85}}
                }
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        fixed_df = apply_fixes(df, fix_plan, "target")
        
        assert "target_enc_feature" in fixed_df.columns
        assert len(fixed_df) == 3
        # 检查是否有修复元数据
        assert 'leakage_buster_fixes' in fixed_df.attrs
    
    def test_get_fix_summary(self):
        """测试修复摘要"""
        risks = [
            {
                "name": "Target leakage (high correlation)",
                "severity": "high",
                "evidence": {"columns": {"amount": 0.99}}
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        summary = get_fix_summary(fix_plan)
        
        assert summary["total_risks"] == 1
        assert summary["high_risk_items"] == 1
        assert summary["delete_columns"] == 1
        assert "created_at" in summary
    
    def test_validate_fix_plan(self):
        """测试修复计划验证"""
        risks = [
            {
                "name": "Target leakage (high correlation)",
                "severity": "high",
                "evidence": {"columns": {"amount": 0.99}}
            }
        ]
        
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        validation = validate_fix_plan(fix_plan)
        
        assert not validation["valid"]  # 有高危项目，所以无效
        assert len(validation["issues"]) > 0
        assert "高危风险项" in validation["issues"][0]

class TestAPI:
    """测试API"""
    
    def test_audit_basic(self):
        """测试基础审计"""
        df = pd.DataFrame({
            'amount': np.random.normal(100, 20, 50),
            'target': np.random.binomial(1, 0.3, 50)
        })
        
        audit_result = audit(df, 'target')
        
        assert isinstance(audit_result, AuditResult)
        assert audit_result.meta["target"] == "target"
        assert audit_result.risk_count >= 0
        assert not audit_result.has_high_risk  # 随机数据不应该有高危风险
    
    def test_audit_with_high_correlation(self):
        """测试高相关性审计"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500],
            'target': [0, 1, 0, 1, 0]
        })
        # 创建高相关性
        df['leak_col'] = df['target'] * 100 + np.random.normal(0, 0.1, 5)
        
        audit_result = audit(df, 'target')
        
        # 应该检测到高相关性风险
        assert audit_result.risk_count > 0
    
    def test_plan_fixes(self):
        """测试修复计划"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500],
            'target': [0, 1, 0, 1, 0]
        })
        df['leak_col'] = df['target'] * 100 + np.random.normal(0, 0.1, 5)
        
        audit_result = audit(df, 'target')
        fix_plan = plan_fixes(audit_result, "test.csv")
        
        assert isinstance(fix_plan, FixPlan)
        assert fix_plan.total_risks > 0
    
    def test_apply_fixes_to_dataframe(self):
        """测试应用修复到数据框"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500],
            'target': [0, 1, 0, 1, 0]
        })
        df['leak_col'] = df['target'] * 100 + np.random.normal(0, 0.1, 5)
        
        audit_result = audit(df, 'target')
        fix_plan = plan_fixes(audit_result, "test.csv")
        fixed_df = apply_fixes_to_dataframe(df, fix_plan)
        
        assert isinstance(fixed_df, pd.DataFrame)
        assert len(fixed_df) == len(df)
        assert 'leakage_buster_fixes' in fixed_df.attrs

class TestCLIIntegration:
    """测试CLI集成"""
    
    def test_cli_auto_fix_plan(self):
        """测试CLI auto-fix plan模式"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500],
            'target': [0, 1, 0, 1, 0]
        })
        df['leak_col'] = df['target'] * 100 + np.random.normal(0, 0.1, 5)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f, index=False)
            data_file = f.name
        
        try:
            result = run(
                train_path=data_file,
                target='target',
                time_col=None,
                out_dir='test_plan_output',
                auto_fix='plan',
                fix_json='test_plan_output/fix_plan.json'
            )
            
            assert result['status'] == 'success'
            assert 'fix_plan' in result['data']
            assert os.path.exists('test_plan_output/fix_plan.json')
            
            # 验证修复计划JSON
            with open('test_plan_output/fix_plan.json', 'r') as f:
                plan_data = json.load(f)
            assert 'version' in plan_data
            assert 'total_risks' in plan_data
            
        finally:
            os.unlink(data_file)
            if os.path.exists('test_plan_output'):
                import shutil
                shutil.rmtree('test_plan_output')
    
    def test_cli_auto_fix_apply(self):
        """测试CLI auto-fix apply模式"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500],
            'target': [0, 1, 0, 1, 0]
        })
        df['leak_col'] = df['target'] * 100 + np.random.normal(0, 0.1, 5)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f, index=False)
            data_file = f.name
        
        try:
            result = run(
                train_path=data_file,
                target='target',
                time_col=None,
                out_dir='test_apply_output',
                auto_fix='apply',
                fixed_train='test_apply_output/fixed_train.csv'
            )
            
            assert result['status'] == 'success'
            assert os.path.exists('test_apply_output/fixed_train.csv')
            
            # 验证修复后的数据
            fixed_df = pd.read_csv('test_apply_output/fixed_train.csv')
            assert len(fixed_df) == len(df)
            assert 'target' in fixed_df.columns
            
        finally:
            os.unlink(data_file)
            if os.path.exists('test_apply_output'):
                import shutil
                shutil.rmtree('test_apply_output')
    
    def test_cli_exit_codes(self):
        """测试CLI退出码"""
        # 测试正常情况
        df = pd.DataFrame({
            'amount': np.random.normal(100, 20, 50),
            'target': np.random.binomial(1, 0.3, 50)
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f, index=False)
            data_file = f.name
        
        try:
            result = run(
                train_path=data_file,
                target='target',
                time_col=None,
                out_dir='test_exit_output'
            )
            
            assert result['exit_code'] == EXIT_OK
            
        finally:
            os.unlink(data_file)
            if os.path.exists('test_exit_output'):
                import shutil
                shutil.rmtree('test_exit_output')
    
    def test_cli_invalid_config(self):
        """测试CLI无效配置"""
        result = run(
            train_path='nonexistent.csv',
            target='target',
            time_col=None,
            out_dir='test_invalid_output'
        )
        
        assert result['status'] == 'error'
        assert result['exit_code'] == EXIT_INVALID_CONFIG

class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_risks(self):
        """测试空风险列表"""
        risks = []
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        
        assert fix_plan.total_risks == 0
        assert fix_plan.high_risk_items == 0
        assert len(fix_plan.delete_columns) == 0
    
    def test_apply_fixes_no_changes(self):
        """测试无变化的修复应用"""
        df = pd.DataFrame({
            'amount': [100, 200, 300],
            'target': [0, 1, 0]
        })
        
        risks = []
        fix_plan = create_fix_plan(risks, "test.csv", "target")
        fixed_df = apply_fixes(df, fix_plan, "target")
        
        assert len(fixed_df) == len(df)
        assert list(fixed_df.columns) == list(df.columns)
    
    def test_audit_result_properties(self):
        """测试审计结果属性"""
        df = pd.DataFrame({
            'amount': [100, 200, 300],
            'target': [0, 1, 0]
        })
        
        audit_result = audit(df, 'target')
        
        assert audit_result.risk_count >= 0
        assert audit_result.high_risk_count >= 0
        assert audit_result.medium_risk_count >= 0
        assert audit_result.low_risk_count >= 0
        assert isinstance(audit_result.has_high_risk, bool)
        assert isinstance(audit_result.has_medium_risk, bool)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
