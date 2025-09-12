
import pytest
import pandas as pd
import numpy as np
import os
import sys
import yaml
import json
import tempfile

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from leakage_buster.core.cv_policy import CVPolicyAuditor, audit_cv_policy, CVPolicy
from leakage_buster.core.export import ReportExporter, export_report
from leakage_buster.cli import run

class TestCVPolicyAuditor:
    """测试CV策略审计器"""
    
    def test_load_policy(self):
        """测试加载策略文件"""
        # 创建临时策略文件
        policy_data = {
            'cv_type': 'timeseries',
            'n_splits': 5,
            'time_col': 'date',
            'group_cols': ['user_id'],
            'sampling_strategy': 'time_aware',
            'random_state': 42
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            auditor = CVPolicyAuditor()
            success = auditor.load_policy(policy_file)
            
            assert success == True
            assert auditor.policy is not None
            assert auditor.policy.cv_type == 'timeseries'
            assert auditor.policy.time_col == 'date'
            assert auditor.policy.group_cols == ['user_id']
        finally:
            os.unlink(policy_file)
    
    def test_audit_data_cv_type_mismatch(self):
        """测试CV类型不匹配检测"""
        # 创建测试数据
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=50, freq='D'),
            'user_id': ['user_001'] * 50,
            'amount': np.random.normal(100, 20, 50),
            'y': np.random.binomial(1, 0.3, 50)
        })
        
        # 创建策略（要求kfold但数据有时序特征）
        policy = CVPolicy(
            cv_type='kfold',
            n_splits=5,
            time_col='date',
            group_cols=[],
            sampling_strategy='random',
            random_state=42
        )
        
        auditor = CVPolicyAuditor()
        auditor.policy = policy
        
        result = auditor.audit_data(df, 'y', 'date')
        
        assert result['status'] == 'audited'
        assert len(result['violations']) > 0
        
        # 应该检测到CV类型不匹配
        cv_violations = [v for v in result['violations'] if v['violation_type'] == 'cv_type_mismatch']
        assert len(cv_violations) > 0
        assert cv_violations[0]['severity'] == 'high'  # 时间数据用KFold是严重错误
    
    def test_audit_data_missing_group_columns(self):
        """测试缺失分组列检测"""
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=50, freq='D'),
            'amount': np.random.normal(100, 20, 50),
            'y': np.random.binomial(1, 0.3, 50)
        })
        
        policy = CVPolicy(
            cv_type='group',
            n_splits=5,
            time_col='date',
            group_cols=['user_id', 'merchant_id'],
            sampling_strategy='time_aware',
            random_state=42
        )
        
        auditor = CVPolicyAuditor()
        auditor.policy = policy
        
        result = auditor.audit_data(df, 'y', 'date')
        
        # 应该检测到缺失分组列
        missing_violations = [v for v in result['violations'] if v['violation_type'] == 'missing_group_columns']
        assert len(missing_violations) > 0
        assert missing_violations[0]['severity'] == 'high'
    
    def test_audit_data_insufficient_data(self):
        """测试数据量不足检测"""
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=5, freq='D'),
            'amount': np.random.normal(100, 20, 5),
            'y': np.random.binomial(1, 0.3, 5)
        })
        
        policy = CVPolicy(
            cv_type='timeseries',
            n_splits=5,  # 需要至少10行数据
            time_col='date',
            group_cols=[],
            sampling_strategy='time_aware',
            random_state=42
        )
        
        auditor = CVPolicyAuditor()
        auditor.policy = policy
        
        result = auditor.audit_data(df, 'y', 'date')
        
        # 应该检测到数据量不足
        insufficient_violations = [v for v in result['violations'] if v['violation_type'] == 'insufficient_data']
        assert len(insufficient_violations) > 0
        assert insufficient_violations[0]['severity'] == 'high'
    
    def test_audit_data_compliant(self):
        """测试合规数据"""
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=100, freq='D'),
            'user_id': ['user_001'] * 100,
            'amount': np.random.normal(100, 20, 100),
            'y': np.random.binomial(1, 0.3, 100)
        })
        
        policy = CVPolicy(
            cv_type='timeseries',
            n_splits=5,
            time_col='date',
            group_cols=['user_id'],
            sampling_strategy='time_aware',
            random_state=42
        )
        
        auditor = CVPolicyAuditor()
        auditor.policy = policy
        
        result = auditor.audit_data(df, 'y', 'date')
        
        assert result['status'] == 'audited'
        # 应该没有违规
        assert len(result['violations']) == 0
        assert result['summary']['compliance_status'] == 'compliant'
    
    def test_audit_cv_policy_convenience_function(self):
        """测试便捷函数"""
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=50, freq='D'),
            'amount': np.random.normal(100, 20, 50),
            'y': np.random.binomial(1, 0.3, 50)
        })
        
        # 创建临时策略文件
        policy_data = {
            'cv_type': 'kfold',
            'n_splits': 5,
            'time_col': 'date'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            result = audit_cv_policy(df, 'y', 'date', policy_file)
            
            assert result['status'] == 'audited'
            assert 'violations' in result
            assert 'summary' in result
        finally:
            os.unlink(policy_file)

class TestReportExporter:
    """测试报告导出器"""
    
    def test_export_pdf_fallback(self):
        """测试PDF导出回退"""
        exporter = ReportExporter()
        
        # 创建临时HTML文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write('<html><body><h1>Test</h1></body></html>')
            html_file = f.name
        
        try:
            pdf_file = html_file.replace('.html', '.pdf')
            result = exporter.export_pdf(html_file, pdf_file)
            
            # 应该回退到HTML（因为weasyprint可能不可用）
            assert result['status'] in ['success', 'fallback']
            if result['status'] == 'fallback':
                assert 'install_hint' in result
        finally:
            os.unlink(html_file)
            if os.path.exists(html_file.replace('.html', '.pdf')):
                os.unlink(html_file.replace('.html', '.pdf'))
    
    def test_export_sarif(self):
        """测试SARIF导出"""
        exporter = ReportExporter()
        
        # 创建测试结果
        results = {
            'risks': [
                {
                    'name': 'Target leakage (high correlation)',
                    'severity': 'high',
                    'detail': 'Test risk',
                    'evidence': {'columns': {'test_col': 0.99}},
                    'leak_score': 0.9
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
            sarif_file = f.name
        
        try:
            result = exporter.export_sarif(results, sarif_file)
            
            assert result['status'] == 'success'
            assert result['output_file'] == sarif_file
            assert result['results_count'] > 0
            
            # 验证SARIF文件内容
            with open(sarif_file, 'r') as f:
                sarif_data = json.load(f)
            
            assert sarif_data['$schema'] is not None
            assert 'runs' in sarif_data
            assert len(sarif_data['runs']) > 0
            assert 'results' in sarif_data['runs'][0]
        finally:
            os.unlink(sarif_file)
    
    def test_export_convenience_function(self):
        """测试便捷函数"""
        # 创建测试结果
        results = {
            'risks': [
                {
                    'name': 'Test risk',
                    'severity': 'medium',
                    'detail': 'Test detail',
                    'evidence': {},
                    'leak_score': 0.5
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
            sarif_file = f.name
        
        try:
            result = export_report(None, sarif_file, 'sarif', results)
            
            assert result['status'] == 'success'
            assert result['output_file'] == sarif_file
        finally:
            os.unlink(sarif_file)

class TestCLIIntegration:
    """测试CLI集成"""
    
    def test_cli_with_cv_policy(self):
        """测试带CV策略的CLI"""
        # 创建测试数据
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=50, freq='D'),
            'user_id': ['user_001'] * 50,
            'amount': np.random.normal(100, 20, 50),
            'y': np.random.binomial(1, 0.3, 50)
        })
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f, index=False)
            data_file = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            policy_data = {
                'cv_type': 'timeseries',
                'n_splits': 5,
                'time_col': 'date',
                'group_cols': ['user_id']
            }
            yaml.dump(policy_data, f)
            policy_file = f.name
        
        try:
            result = run(
                train_path=data_file,
                target='y',
                time_col='date',
                out_dir='test_cv_policy_output',
                cv_type='timeseries',
                simulate_cv=None,
                leak_threshold=0.02,
                cv_policy_file=policy_file,
                export=None,
                export_sarif=None
            )
            
            assert result['status'] == 'success'
            assert 'policy_audit' in result['data']
            assert result['data']['policy_audit']['status'] == 'audited'
        finally:
            os.unlink(data_file)
            os.unlink(policy_file)
            if os.path.exists('test_cv_policy_output'):
                import shutil
                shutil.rmtree('test_cv_policy_output')
    
    def test_cli_with_export(self):
        """测试带导出的CLI"""
        # 创建测试数据
        df = pd.DataFrame({
            'date': pd.date_range('2023-01-01', periods=30, freq='D'),
            'amount': np.random.normal(100, 20, 30),
            'y': np.random.binomial(1, 0.3, 30)
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df.to_csv(f, index=False)
            data_file = f.name
        
        try:
            result = run(
                train_path=data_file,
                target='y',
                time_col='date',
                out_dir='test_export_output',
                cv_type='timeseries',
                simulate_cv=None,
                leak_threshold=0.02,
                cv_policy_file=None,
                export='pdf',
                export_sarif='test_export_output/leakage.sarif'
            )
            
            assert result['status'] == 'success'
            assert 'exports' in result['data']
            
            # 检查导出结果
            if 'pdf' in result['data']['exports']:
                pdf_result = result['data']['exports']['pdf']
                assert pdf_result['status'] in ['success', 'fallback']
            
            if 'sarif' in result['data']['exports']:
                sarif_result = result['data']['exports']['sarif']
                assert sarif_result['status'] == 'success'
        finally:
            os.unlink(data_file)
            if os.path.exists('test_export_output'):
                import shutil
                shutil.rmtree('test_export_output')

class TestEdgeCases:
    """测试边界情况"""
    
    def test_missing_policy_file(self):
        """测试缺失策略文件"""
        df = pd.DataFrame({
            'amount': np.random.normal(100, 20, 30),
            'y': np.random.binomial(1, 0.3, 30)
        })
        
        result = audit_cv_policy(df, 'y', None, 'nonexistent.yaml')
        
        assert result['status'] == 'no_policy'
        assert 'No policy file loaded' in result['message']
    
    def test_invalid_policy_file(self):
        """测试无效策略文件"""
        df = pd.DataFrame({
            'amount': np.random.normal(100, 20, 30),
            'y': np.random.binomial(1, 0.3, 30)
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('invalid: yaml: content: [')
            policy_file = f.name
        
        try:
            result = audit_cv_policy(df, 'y', None, policy_file)
            
            assert result['status'] == 'no_policy'
        finally:
            os.unlink(policy_file)
    
    def test_empty_results_sarif(self):
        """测试空结果的SARIF导出"""
        exporter = ReportExporter()
        
        results = {'risks': []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sarif', delete=False) as f:
            sarif_file = f.name
        
        try:
            result = exporter.export_sarif(results, sarif_file)
            
            assert result['status'] == 'success'
            assert result['results_count'] == 0
        finally:
            os.unlink(sarif_file)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
