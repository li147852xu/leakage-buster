# Leakage Buster / 泄漏检测器

[![PyPI version](https://img.shields.io/pypi/v/leakage-buster.svg)](https://pypi.org/project/leakage-buster/)
[![Python](https://img.shields.io/pypi/pyversions/leakage-buster.svg)](https://pypi.org/project/leakage-buster/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/li147852xu/leakage-buster/actions/workflows/ci.yml/badge.svg)](https://github.com/li147852xu/leakage-buster/actions/workflows/ci.yml)

> **Professional Data Leakage Detection & Audit Tool** | 专业的数据泄漏检测与审计工具  
> Detects time leakage, KFold leakage, and CV consistency issues with detailed reports and fix suggestions.

## 🚀 Quick Start / 快速开始

### Installation / 安装

```bash
# Install from PyPI (自动检测依赖)
pip install leakage-buster

# With optional PDF export support
pip install "leakage-buster[pdf]"

# With optional Polars engine (faster processing)
pip install "leakage-buster[polars]"

# With all optional features
pip install "leakage-buster[pdf,polars]"
```

**✅ Automatic Dependency Detection / 自动依赖检测**  
When you install via `pip install leakage-buster`, pip automatically:
- Installs all required dependencies (pandas, numpy, scikit-learn, jinja2, etc.)
- Resolves version conflicts
- Creates proper dependency tree
- No manual dependency management needed!

📖 **For detailed installation guide, see [INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md)**

### Basic Usage / 基本使用

```bash
# Quick test with example data
leakage-buster run \
  --train examples/quick_start_example.csv \
  --target target \
  --time-col date \
  --out test_results

# Basic audit with your data
leakage-buster run \
  --train your_data.csv \
  --target target_column \
  --out audit_results

# With time column
leakage-buster run \
  --train your_data.csv \
  --target target_column \
  --time-col date_column \
  --out audit_results

# Advanced features
leakage-buster run \
  --train your_data.csv \
  --target target_column \
  --time-col date_column \
  --simulate-cv time \
  --auto-fix plan \
  --export pdf \
  --out audit_results
```

## 📋 What It Does / 功能说明

### Problem It Solves / 解决的问题
- **Time Leakage**: Future data accidentally used in training | 时间泄漏：训练时意外使用未来数据
- **Target Leakage**: Target information leaked into features | 目标泄漏：目标信息泄漏到特征中
- **CV Leakage**: Wrong cross-validation strategy | 交叉验证泄漏：错误的CV策略
- **Statistical Leakage**: Target encoding, WOE, rolling stats issues | 统计泄漏：目标编码、WOE、滚动统计问题

### Detection Capabilities / 检测能力

| Detection Type | Description | 中文说明 |
|----------------|-------------|----------|
| **Target Leakage** | High correlation features (|corr|/R²≥0.98) | 高相关性特征检测 |
| **Statistical Leakage** | TE/WOE/Rolling statistics issues | 统计类泄漏检测 |
| **Time Leakage** | Time column parsing and validation | 时间列解析与验证 |
| **Group Leakage** | High duplicate columns → GroupKFold | 分组泄漏检测 |
| **CV Consistency** | TimeSeriesSplit vs KFold vs GroupKFold | CV策略一致性 |
| **Policy Audit** | Offline/Online calibration differences | 口径一致性审计 |

## 🔧 Core Features / 核心特性

### 🔍 Comprehensive Detection / 全面检测
- **Target Leakage**: High correlation, categorical purity anomalies
- **Statistical Leakage**: Target encoding (TE), WOE, rolling statistics, aggregation traces
- **Time Leakage**: Time column parsing, time-aware suggestions
- **Group Leakage**: High duplicate columns → GroupKFold recommendations
- **CV Strategy**: TimeSeriesSplit vs KFold vs GroupKFold recommendations
- **Policy Audit**: Offline/online calibration consistency checks

### ⚡ High Performance / 高性能处理
- **Multi-Engine Support**: pandas (default), polars (optional)
- **Parallel Processing**: Multi-core detection with `--n-jobs`
- **Memory Control**: Smart memory management with `--memory-cap`
- **Large Data Support**: Chunking and sampling for million-row datasets
- **Performance Optimization**: Automatic data type optimization

### 🔧 Semi-Automatic Repair / 半自动修复
- **Fix Plan Generation**: Structured repair suggestions JSON
- **Automatic Fix Application**: Apply fixes based on plan
- **Smart Suggestions**: Delete/recalculate/recommend CV & groups
- **Evidence Tracking**: Record source risks and reasoning

### 📊 Professional Reports / 专业报告
- **Interactive Reports**: Risk radar charts, risk matrices, collapsible evidence
- **Multi-Format Export**: HTML, PDF, SARIF (GitHub Code Scanning)
- **Detailed Metadata**: Git hash, random seed, system info
- **Responsive Design**: Mobile and print support

### 🐍 Stable SDK / 稳定SDK
- **Python API**: `audit()`, `plan_fixes()`, `apply_fixes()`
- **Type Safety**: Complete type annotations and Pydantic models
- **CI-Friendly**: Standardized exit codes and error handling
- **Well Documented**: Detailed API documentation and examples

## 📋 Complete Parameter Reference / 完整参数表

### Basic Parameters / 基础参数
| Parameter | Type | Default | Description | 中文说明 |
|-----------|------|---------|-------------|----------|
| `--train` | str | Required | Training data CSV file path | 训练数据CSV文件路径 |
| `--target` | str | Required | Target column name | 目标列名 |
| `--time-col` | str | None | Time column name (optional) | 时间列名（可选） |
| `--out` | str | Required | Output directory | 输出目录 |

### CV Strategy Parameters / CV策略参数
| Parameter | Type | Default | Description | 中文说明 |
|-----------|------|---------|-------------|----------|
| `--cv-type` | str | None | CV strategy: kfold/timeseries/group | CV策略：kfold/timeseries/group |
| `--simulate-cv` | str | None | Enable time simulation: time | 启用时序模拟：time |
| `--leak-threshold` | float | 0.02 | Leakage threshold | 泄漏阈值 |
| `--cv-policy-file` | str | None | CV policy config file (YAML) | CV策略配置文件（YAML） |

### Performance Parameters / 性能参数
| Parameter | Type | Default | Description | 中文说明 |
|-----------|------|---------|-------------|----------|
| `--engine` | str | pandas | Data engine: pandas/polars | 数据引擎：pandas/polars |
| `--n-jobs` | int | -1 | Parallel jobs (-1=auto) | 并行作业数（-1=自动） |
| `--memory-cap` | int | 4096 | Memory limit (MB) | 内存限制（MB） |
| `--sample-ratio` | float | None | Sampling ratio for large datasets | 大数据集采样比例 |

### Export Parameters / 导出参数
| Parameter | Type | Default | Description | 中文说明 |
|-----------|------|---------|-------------|----------|
| `--export` | str | None | Export format: pdf | 导出格式：pdf |
| `--export-sarif` | str | None | SARIF file path (GitHub Code Scanning) | SARIF文件路径 |

### Auto-Fix Parameters / 自动修复参数
| Parameter | Type | Default | Description | 中文说明 |
|-----------|------|---------|-------------|----------|
| `--auto-fix` | str | None | Auto-fix mode: plan/apply | 自动修复模式：plan/apply |
| `--fix-json` | str | None | Fix plan JSON output path | 修复计划JSON输出路径 |
| `--fixed-train` | str | None | Fixed data CSV output path | 修复后数据CSV输出路径 |

## 📊 Usage Examples / 使用示例

### Example 1: Basic Audit / 基础审计
```bash
# Detect all types of leakage
leakage-buster run \
  --train data/train.csv \
  --target target \
  --out results/basic_audit

# Output files:
# - results/basic_audit/report.html
# - results/basic_audit/fix_transforms.py
# - results/basic_audit/meta.json
```

### Example 2: Time Series Analysis / 时序分析
```bash
# Time-aware analysis with simulation
leakage-buster run \
  --train data/time_series.csv \
  --target target \
  --time-col timestamp \
  --simulate-cv time \
  --leak-threshold 0.05 \
  --out results/time_audit
```

### Example 3: High Performance / 高性能处理
```bash
# Use Polars engine with parallel processing
leakage-buster run \
  --train data/large_dataset.csv \
  --target target \
  --engine polars \
  --n-jobs 8 \
  --memory-cap 8192 \
  --sample-ratio 0.1 \
  --out results/perf_audit
```

### Example 4: Auto-Fix / 自动修复
```bash
# Generate fix plan
leakage-buster run \
  --train data/problematic_data.csv \
  --target target \
  --auto-fix plan \
  --fix-json results/fix_plan.json \
  --out results/audit

# Apply fixes
leakage-buster run \
  --train data/problematic_data.csv \
  --target target \
  --auto-fix apply \
  --fixed-train results/fixed_data.csv \
  --out results/final_audit
```

### Example 5: Professional Export / 专业导出
```bash
# Export PDF report and SARIF for GitHub
leakage-buster run \
  --train data/production_data.csv \
  --target target \
  --time-col date \
  --export pdf \
  --export-sarif results/leakage.sarif \
  --out results/production_audit
```

## 🐳 Docker Usage / Docker使用

### Build Image / 构建镜像
```bash
docker build -t leakage-buster .
```

### Run Container / 运行容器
```bash
# Basic usage
docker run -v $(pwd):/data leakage-buster run \
  --train /data/data.csv --target y --out /data/output

# High performance
docker run -v $(pwd):/data leakage-buster run \
  --train /data/data.csv --target y --out /data/output \
  --engine pandas --n-jobs 8 --memory-cap 4096
```

## 🔄 CI/CD Integration / CI/CD集成

### GitHub Actions Example / GitHub Actions示例
```yaml
- name: Run leakage audit
  run: |
    leakage-buster run --train data/train.csv --target y --time-col date --out runs/audit
    if [ $? -eq 3 ]; then
      echo "❌ High leakage detected! Build failed."
      exit 1
    fi
```

### Exit Codes / 退出码规范
| Code | Meaning | Description | 中文说明 |
|------|---------|-------------|----------|
| **0** | Success | No risks detected | 成功，无风险 |
| **2** | Warning | Medium/low risks detected | 警告，有中低危风险 |
| **3** | High Risk | High leakage detected | 高危泄漏，需要立即处理 |
| **4** | Error | Configuration error | 配置错误，无法执行 |

## 🐍 Python SDK / Python SDK

### Basic Usage / 基本使用
```python
import pandas as pd
from leakage_buster.api import audit, plan_fixes, apply_fixes_to_dataframe

# Load data
df = pd.read_csv('data/train.csv')

# Run audit
audit_result = audit(df, target='target', time_col='date')

# Generate fix plan
fix_plan = plan_fixes(audit_result, 'data/train.csv')

# Apply fixes
fixed_df = apply_fixes_to_dataframe(df, fix_plan)

# Check results
print(f"Found {len(audit_result.risks)} risks")
print(f"High risks: {audit_result.has_high_risk}")
```

### Advanced Usage / 高级使用
```python
from leakage_buster.api import audit
from leakage_buster.core import DataLoader, ParallelProcessor

# Custom data loading
loader = DataLoader(engine='polars', memory_cap=4096)
df = loader.load('data/large_dataset.csv')

# Parallel processing
processor = ParallelProcessor(n_jobs=8)
audit_result = audit(df, target='target', parallel_processor=processor)

# Access detailed results
for risk in audit_result.risks:
    print(f"Risk: {risk.name}")
    print(f"Severity: {risk.severity}")
    print(f"Evidence: {risk.evidence}")
    print(f"Leak Score: {risk.leak_score}")
```

## 📊 Performance Benchmarks / 性能基准

### Test Environment / 测试环境
- **CPU**: 8-core Intel i7
- **Memory**: 16GB RAM
- **Data**: 150K rows × 250 columns

### Performance Metrics / 性能指标
| Metric | pandas | polars | Improvement | 提升 |
|--------|--------|--------|-------------|------|
| Load Time | 15.2s | 8.7s | 1.7x | 1.7倍 |
| Audit Time | 45.3s | 28.1s | 1.6x | 1.6倍 |
| Memory Usage | 2.1GB | 1.4GB | 1.5x | 1.5倍 |
| Parallel Efficiency | 6.2x | 7.8x | 1.3x | 1.3倍 |

## 🧪 Testing / 测试

### Run Tests / 运行测试
```bash
# Run all tests
pytest -q

# Run performance tests
pytest tests/perf/test_perf_medium.py -k perf -s

# Skip slow tests
pytest -q -k "not slow"
```

### Test Coverage / 测试覆盖
- **Unit Tests**: 100% core functionality coverage
- **Integration Tests**: CLI and API end-to-end tests
- **Performance Tests**: Medium-scale dataset tests
- **Security Tests**: Bandit and Safety scans

## 📈 Version History / 版本历史

### v1.0.1 (Current / 当前版本)
- 🔧 Fixed CI test failures / 修复CI测试失败问题
- 🔧 Cleaned up debug files on GitHub / 清理GitHub上的debug文件
- ✨ Added PyPI publishing support / 添加PyPI发布支持
- 🔧 Fixed README badge links / 修复README徽章链接

### v1.0.0
- ✨ Performance & fault tolerance: pandas/polars engines, parallel processing, memory control
- ✨ Professional reports: risk radar charts, interactive UI, multi-format export
- ✨ Docker support: lightweight image, health checks, complete metadata
- ✨ PyPI ready: complete metadata, optional dependencies, test configuration

### v0.5-rc
- ✨ Semi-automatic repair system / 半自动修复系统
- ✨ Stable Python SDK / 稳定Python SDK
- ✨ Standardized exit codes / 标准化退出码

### v0.4.0
- ✨ Calibration consistency audit / 口径一致性审计
- ✨ PDF/SARIF export / PDF/SARIF导出
- ✨ Upgraded report template / 升级报告模板

### v0.3.0
- ✨ Statistical leakage detection / 统计类泄漏检测
- ✨ Time series simulator / 时序模拟器
- ✨ Quantified leak scores / 风险分量化

### v0.2.0
- ✨ Extended detection framework / 扩展检测框架
- ✨ JSON schema contract / JSON schema约定

### v0.1.0
- 🎉 Initial release / 初始版本发布

## 🤝 Contributing / 贡献

We welcome contributions of all kinds! / 我们欢迎各种形式的贡献！

### How to Contribute / 贡献方式
1. **Report Issues**: [GitHub Issues](https://github.com/li147852xu/leakage-buster/issues)
2. **Feature Requests**: [GitHub Discussions](https://github.com/li147852xu/leakage-buster/discussions)
3. **Code Contributions**: Fork → Develop → Pull Request
4. **Documentation**: Direct edits or PR submissions

### Development Environment / 开发环境
```bash
git clone https://github.com/li147852xu/leakage-buster.git
cd leakage-buster
pip install -e ".[dev]"
pytest
```

## 📄 License / 许可证

MIT License - See [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments / 致谢

Thanks to all contributors and users for their support! / 感谢所有贡献者和用户的支持！

---

**Leakage Buster** - Making data leakage nowhere to hide! / 让数据泄漏无处遁形！🕵️‍♂️

[![Star](https://img.shields.io/github/stars/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)
[![Fork](https://img.shields.io/github/forks/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)
[![Watch](https://img.shields.io/github/watchers/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)