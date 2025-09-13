
# Leakage Buster v0.1

> 自动检测时间泄漏 / KFold 泄漏，并生成**修复脚本**与**审计报告**。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 功能特性

### 🔍 核心检测能力
- **目标泄漏检测**：高相关性（|corr|/R²≥0.98）、类别纯度异常
- **时间泄漏检测**：时间列解析、时间感知建议
- **分组泄漏检测**：高重复列→GroupKFold建议
- **CV策略一致性**：TimeSeriesSplit vs KFold vs GroupKFold推荐

### 📊 专业报告
- **HTML报告**：美观的可视化报告
- **修复脚本**：自动生成的Python修复代码
- **JSON输出**：结构化的检测结果

## 🚀 快速开始

### 安装
```bash
pip install -e .
```

### 基本使用
```bash
# 基本检测
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo

# 指定CV策略
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo --cv-type timeseries
```

### 参数说明
- `--train`: 训练数据CSV文件路径
- `--target`: 目标列名
- `--time-col`: 时间列名（可选）
- `--out`: 输出目录
- `--cv-type`: CV策略（kfold/timeseries/group）

## 📁 项目结构

```
leakage-buster/
├── src/leakage_buster/
│   ├── cli.py                 # 命令行接口
│   ├── core/
│   │   ├── checks.py         # 泄漏检测器
│   │   └── report.py         # 报告生成
│   └── templates/
│       └── report.html.j2    # HTML报告模板
├── examples/                 # 示例数据
│   └── synth_train.csv      # 基础示例
├── tests/                   # 测试用例
└── runs/                    # 输出目录
```

## 🔧 检测器详解

### 1. 目标泄漏检测器
- **高相关性检测**：识别与目标高度相关的特征
- **类别纯度检测**：发现几乎完美预测目标的类别

### 2. 分组泄漏检测器
- **高重复列检测**：识别需要GroupKFold的列
- **CV策略推荐**：根据数据特征推荐合适的CV策略

### 3. 时间泄漏检测器
- **时间列解析**：验证时间列格式和有效性
- **时间感知建议**：推荐时间感知的特征工程策略

## 📈 输出示例

### JSON输出
```json
{
  "status": "success",
  "exit_code": 0,
  "data": {
    "report": "runs/demo/report.html",
    "fix_script": "runs/demo/fix_transforms.py",
    "risks": [
      {
        "name": "Target leakage (high correlation)",
        "severity": "high",
        "detail": "Feature 'amount' has correlation 0.99 with target"
      }
    ]
  }
}
```

## 🧪 测试

```bash
# 运行所有测试
pytest -q

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/test
```

## 📋 版本历史

### v0.1.0
- 🎉 初始版本发布
- ✨ 基础泄漏检测功能
- ✨ HTML报告生成
- ✨ 修复脚本生成
- ✨ JSON输出格式

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

**Leakage Buster** - 让数据泄漏无处遁形！🕵️‍♂️
