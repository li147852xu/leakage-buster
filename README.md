
# Leakage Buster v0.2

> 自动检测时间泄漏 / KFold 泄漏 / 口径不一致，并生成**修复脚本**与**审计报告**。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 功能特性

### 🔍 泄漏检测
- **目标泄漏检测**: 识别与目标高度相关的特征
- **目标编码泄漏**: 检测疑似目标编码特征
- **时间窗口泄漏**: 识别全量统计vs窗口内统计问题
- **分组泄漏检测**: 建议使用GroupKFold避免组间泄漏
- **CV策略一致性**: 自动推荐合适的交叉验证策略

### 📊 统计类泄漏（预览）
- 检测疑似统计特征（变异系数较小的数值特征）
- 为未来完善统计类泄漏检测预留接口

### 🛠️ 输出功能
- **HTML报告**: 可视化风险项和修复建议
- **修复脚本**: 自动生成Python修复代码
- **JSON输出**: 结构化数据，便于系统集成

## 🚀 快速开始

### 安装

```bash
pip install -e .
```

### 基础用法

```bash
# 基础检测
leakage-buster run --train data.csv --target y --out results/

# 时间序列数据
leakage-buster run \
  --train data.csv \
  --target y \
  --time-col timestamp \
  --cv-type timeseries \
  --out results/

# 分组数据
leakage-buster run \
  --train data.csv \
  --target y \
  --cv-type group \
  --out results/
```

## 📋 参数说明

| 参数 | 必需 | 描述 | 示例 |
|------|------|------|------|
| `--train` | ✅ | 训练数据CSV文件路径 | `--train data/train.csv` |
| `--target` | ✅ | 目标列名称 | `--target y` |
| `--out` | ✅ | 输出目录路径 | `--out runs/audit_2024` |
| `--time-col` | ❌ | 时间列名称 | `--time-col date` |
| `--cv-type` | ❌ | CV策略类型 | `--cv-type timeseries` |

### CV策略类型

- `kfold`: 标准K折交叉验证（无时间依赖的独立样本）
- `timeseries`: 时间序列分割（有时间顺序的数据）
- `group`: 分组交叉验证（有分组结构的数据）

## 📁 输出文件

执行成功后，在输出目录中生成：

| 文件名 | 描述 |
|--------|------|
| `report.html` | 可视化审计报告 |
| `fix_transforms.py` | 修复建议代码 |
| `meta.json` | 元数据和参数信息 |

## 🔧 检测器架构

项目采用模块化检测器架构，便于扩展：

```python
from leakage_buster.core.checks import DetectorRegistry

# 获取所有检测器
registry = DetectorRegistry()
for detector in registry.detectors:
    risks = detector.detect(df, target, time_col)
```

### 内置检测器

- `TargetLeakageDetector`: 目标泄漏检测
- `TargetEncodingLeakageDetector`: 目标编码泄漏检测
- `KFoldGroupLeakageDetector`: 分组泄漏检测
- `TimeColumnIssuesDetector`: 时间列问题检测
- `CVConsistencyDetector`: CV策略一致性检测
- `StatisticalLeakageDetector`: 统计类泄漏检测（预览）

## 📊 JSON Schema

### 成功输出格式

```json
{
  "status": "success",
  "exit_code": 0,
  "data": {
    "report": "path/to/report.html",
    "fix_script": "path/to/fix_transforms.py",
    "meta": {...},
    "risks": [...]
  }
}
```

### 退出码定义

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 2 | 参数错误 |
| 3 | 文件错误 |
| 4 | 运行时错误 |

详细规范见 [JSON Schema 文档](docs/json_schema.md)

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_schema.py -v

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo
```

## 📚 文档

- [CLI参数规范](docs/cli_flags.md)
- [JSON Schema规范](docs/json_schema.md)
- [与tabular-agent集成指南](docs/json_schema.md#与-tabular-agent-集成)

## 🔄 与 tabular-agent 集成

```python
import subprocess
import json

def audit_dataset(train_path, target_col, time_col=None, cv_type=None):
    """执行数据泄漏审计"""
    cmd = [
        "leakage-buster", "run",
        "--train", train_path,
        "--target", target_col,
        "--out", "runs/audit"
    ]
    
    if time_col:
        cmd.extend(["--time-col", time_col])
    if cv_type:
        cmd.extend(["--cv-type", cv_type])
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
```

## 🛠️ 开发

### 添加新检测器

```python
from leakage_buster.core.checks import BaseDetector, RiskItem

class MyCustomDetector(BaseDetector):
    def __init__(self):
        super().__init__("my_custom_detector")
    
    def detect(self, df, target, time_col=None, **kwargs):
        risks = []
        # 实现检测逻辑
        return risks
```

### 运行开发测试

```bash
# 安装开发依赖
pip install -e .

# 运行测试
pytest tests/ -v

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/v02_demo
```

## 📈 版本历史

### v0.2.0
- ✨ 新增统计类泄漏检测框架（预览版）
- 🔧 重构检测器架构，支持模块化扩展
- 📊 增强HTML报告，新增统计类泄漏预览分区
- 📋 完善JSON Schema和退出码定义
- 🔗 优化与tabular-agent的集成接口
- 📚 新增详细文档和CLI参数规范

### v0.1.0
- 🎯 基础泄漏检测功能
- 📊 HTML报告生成
- 🛠️ 修复脚本生成

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**注意**: 统计类泄漏检测功能为预览版，具体实现将在后续版本中完善。
