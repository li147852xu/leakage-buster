# Installation & Usage Guide / 安装使用指南

## 📦 Installation Process / 安装流程

### Step 1: Install via pip / 通过pip安装

```bash
# Basic installation (自动检测所有依赖)
pip install leakage-buster

# Verify installation
leakage-buster --help
```

**What happens during installation / 安装过程中发生了什么:**

1. **Dependency Resolution / 依赖解析**: pip automatically resolves and installs:
   - `pandas>=2.0,<3.0` - Data manipulation
   - `numpy>=1.23,<2.0` - Numerical computing  
   - `scikit-learn>=1.2,<2.0` - Machine learning
   - `jinja2>=3.1,<4.0` - Template engine
   - `pyyaml>=6.0` - YAML parsing
   - `pydantic>=2.0` - Data validation
   - `psutil>=5.9` - System monitoring

2. **Version Conflict Resolution / 版本冲突解决**: pip ensures all packages are compatible

3. **Entry Point Registration / 入口点注册**: The `leakage-buster` command is registered in your PATH

### Step 2: Optional Dependencies / 可选依赖

```bash
# For PDF export support
pip install "leakage-buster[pdf]"
# Installs: weasyprint>=61

# For faster processing with Polars
pip install "leakage-buster[polars]"  
# Installs: polars>=0.20

# For all optional features
pip install "leakage-buster[pdf,polars]"
```

### Step 3: Verify Installation / 验证安装

```bash
# Check version
leakage-buster --version

# Check help
leakage-buster --help

# Run basic test
leakage-buster run --train examples/synth_train.csv --target y --out test_output
```

## 🚀 Usage Workflow / 使用流程

### Basic Workflow / 基本流程

```bash
# 1. Prepare your data
# Your CSV should have:
# - Target column (what you want to predict)
# - Feature columns (input variables)
# - Optional: Time column (for time series data)

# 2. Run basic audit
leakage-buster run \
  --train your_data.csv \
  --target target_column_name \
  --out audit_results

# 3. Check results
ls audit_results/
# - report.html (detailed HTML report)
# - fix_transforms.py (Python script with fix suggestions)
# - meta.json (metadata and configuration)
```

### Advanced Workflow / 高级流程

```bash
# 1. Time series analysis
leakage-buster run \
  --train time_series_data.csv \
  --target target \
  --time-col timestamp \
  --simulate-cv time \
  --leak-threshold 0.05 \
  --out time_audit

# 2. High performance processing
leakage-buster run \
  --train large_dataset.csv \
  --target target \
  --engine polars \
  --n-jobs 8 \
  --memory-cap 8192 \
  --sample-ratio 0.1 \
  --out perf_audit

# 3. Auto-fix workflow
# Step 3a: Generate fix plan
leakage-buster run \
  --train problematic_data.csv \
  --target target \
  --auto-fix plan \
  --fix-json fix_plan.json \
  --out audit

# Step 3b: Apply fixes
leakage-buster run \
  --train problematic_data.csv \
  --target target \
  --auto-fix apply \
  --fixed-train fixed_data.csv \
  --out final_audit

# 4. Professional export
leakage-buster run \
  --train production_data.csv \
  --target target \
  --time-col date \
  --export pdf \
  --export-sarif results/leakage.sarif \
  --out production_audit
```

## 📊 Understanding Results / 理解结果

### Output Files / 输出文件

| File | Description | 中文说明 |
|------|-------------|----------|
| `report.html` | Interactive HTML report with visualizations | 交互式HTML报告，包含可视化 |
| `fix_transforms.py` | Python script with fix suggestions | Python修复建议脚本 |
| `meta.json` | Metadata and configuration | 元数据和配置信息 |

### Risk Levels / 风险等级

| Level | Color | Action Required | 中文说明 |
|-------|-------|-----------------|----------|
| **High** | 🔴 Red | Immediate action needed | 需要立即处理 |
| **Medium** | 🟡 Yellow | Should be addressed | 应该处理 |
| **Low** | 🟢 Green | Consider for improvement | 可考虑改进 |

### Exit Codes / 退出码

```bash
# Check exit code
echo $?

# 0: Success, no risks
# 2: Warnings, medium/low risks  
# 3: High risks detected
# 4: Configuration error
```

## 🔧 Troubleshooting / 故障排除

### Common Issues / 常见问题

#### 1. Installation Issues / 安装问题

```bash
# If pip fails, try upgrading pip first
pip install --upgrade pip

# If you have permission issues, use --user
pip install --user leakage-buster

# For conda users
conda install -c conda-forge pip
pip install leakage-buster
```

#### 2. Import Errors / 导入错误

```bash
# Check if package is installed
pip show leakage-buster

# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall if needed
pip uninstall leakage-buster
pip install leakage-buster
```

#### 3. Memory Issues / 内存问题

```bash
# Use memory cap for large datasets
leakage-buster run \
  --train large_data.csv \
  --target target \
  --memory-cap 2048 \
  --out results

# Use sampling for very large datasets
leakage-buster run \
  --train huge_data.csv \
  --target target \
  --sample-ratio 0.1 \
  --out results
```

#### 4. Performance Issues / 性能问题

```bash
# Use Polars engine for better performance
pip install "leakage-buster[polars]"

leakage-buster run \
  --train data.csv \
  --target target \
  --engine polars \
  --n-jobs 4 \
  --out results
```

### Getting Help / 获取帮助

```bash
# Command help
leakage-buster --help
leakage-buster run --help

# Check version and system info
leakage-buster --version

# Verbose output for debugging
leakage-buster run \
  --train data.csv \
  --target target \
  --out results \
  --verbose
```

## 🐍 Python SDK Usage / Python SDK使用

### Basic Python Usage / 基本Python使用

```python
import pandas as pd
from leakage_buster.api import audit

# Load your data
df = pd.read_csv('your_data.csv')

# Run audit
result = audit(df, target='target_column', time_col='date_column')

# Check results
print(f"Found {len(result.risks)} risks")
print(f"High risks: {result.has_high_risk}")

# Access individual risks
for risk in result.risks:
    print(f"Risk: {risk.name}")
    print(f"Severity: {risk.severity}")
    print(f"Evidence: {risk.evidence}")
```

### Advanced Python Usage / 高级Python使用

```python
from leakage_buster.api import audit, plan_fixes, apply_fixes_to_dataframe
from leakage_buster.core import DataLoader

# Custom data loading
loader = DataLoader(engine='polars', memory_cap=4096)
df = loader.load('large_dataset.csv')

# Run audit with custom parameters
result = audit(
    df, 
    target='target',
    time_col='date',
    cv_type='timeseries',
    simulate_cv='time',
    leak_threshold=0.05
)

# Generate and apply fixes
fix_plan = plan_fixes(result, 'large_dataset.csv')
fixed_df = apply_fixes_to_dataframe(df, fix_plan)

# Save results
fixed_df.to_csv('fixed_data.csv', index=False)
```

## 🔄 CI/CD Integration / CI/CD集成

### GitHub Actions / GitHub Actions

```yaml
name: Leakage Audit
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install leakage-buster
      run: pip install leakage-buster
    - name: Run audit
      run: |
        leakage-buster run \
          --train data/train.csv \
          --target target \
          --time-col date \
          --out audit_results
    - name: Check for high risks
      run: |
        if [ $? -eq 3 ]; then
          echo "❌ High leakage detected! Build failed."
          exit 1
        fi
    - name: Upload results
      uses: actions/upload-artifact@v2
      with:
        name: audit-results
        path: audit_results/
```

### Jenkins / Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Install') {
            steps {
                sh 'pip install leakage-buster'
            }
        }
        stage('Audit') {
            steps {
                sh '''
                    leakage-buster run \
                      --train data/train.csv \
                      --target target \
                      --out audit_results
                '''
            }
        }
        stage('Check Results') {
            steps {
                script {
                    def exitCode = sh(
                        script: 'leakage-buster run --train data/train.csv --target target --out audit_results; echo $?',
                        returnStdout: true
                    ).trim()
                    
                    if (exitCode == '3') {
                        error 'High leakage detected! Build failed.'
                    }
                }
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'audit_results/**', fingerprint: true
        }
    }
}
```

## 📚 Additional Resources / 额外资源

### Documentation / 文档
- [CLI Flags Reference](cli_flags.md) - Complete CLI parameter reference
- [JSON Schema](json_schema.md) - Output format specification
- [API Reference](api_reference.md) - Python SDK documentation

### Examples / 示例
- [Basic Usage Examples](examples/basic_usage.md)
- [Advanced Scenarios](examples/advanced_scenarios.md)
- [Integration Examples](examples/integration_examples.md)

### Support / 支持
- [GitHub Issues](https://github.com/li147852xu/leakage-buster/issues) - Bug reports and feature requests
- [GitHub Discussions](https://github.com/li147852xu/leakage-buster/discussions) - Community discussions
- [Documentation](https://leakage-buster.readthedocs.io) - Complete documentation
