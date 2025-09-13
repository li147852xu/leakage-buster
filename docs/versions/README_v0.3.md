
# Leakage Buster v0.3

> 自动检测时间泄漏 / KFold 泄漏 / 口径不一致，并生成**修复脚本**与**审计报告**。

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 功能特性

### 🔍 核心检测能力
- **目标泄漏检测**：高相关性（|corr|/R²≥0.98）、类别纯度异常
- **统计类泄漏检测**：目标编码(TE)、WOE、滚动统计、聚合痕迹
- **时间泄漏检测**：时间列解析、时间感知建议
- **分组泄漏检测**：高重复列→GroupKFold建议
- **CV策略一致性**：TimeSeriesSplit vs KFold vs GroupKFold推荐

### ⏰ 时序模拟器 (v0.3新增)
- **对比验证**：TimeSeriesSplit与KFold的OOF指标变化
- **泄漏阈值**：可配置的泄漏检测阈值
- **风险分级**：基于分数差异的严重程度评估
- **量化证据**：结构化的检测证据和风险分

### 📊 专业报告
- **HTML报告**：美观的可视化报告，支持证据展开
- **修复脚本**：自动生成的Python修复代码
- **风险矩阵**：按严重程度分类的风险统计
- **证据详情**：可折叠的详细检测证据

## 🚀 快速开始

### 安装
```bash
pip install -e .
```

### 基本使用
```bash
# 基本检测
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/demo

# 带时序模拟的检测
leakage-buster run --train examples/homecredit_te.csv --target y --time-col date --out runs/v03_te --simulate-cv time --leak-threshold 0.02

# 滚动统计检测
leakage-buster run --train examples/fraud_rolling.csv --target y --time-col ts --out runs/v03_roll --simulate-cv time
```

### 参数说明
- `--train`: 训练数据CSV文件路径
- `--target`: 目标列名
- `--time-col`: 时间列名（可选）
- `--out`: 输出目录
- `--cv-type`: CV策略（kfold/timeseries/group）
- `--simulate-cv`: 启用时序模拟（time）
- `--leak-threshold`: 泄漏阈值（默认0.02）

## 📁 项目结构

```
leakage-buster/
├── src/leakage_buster/
│   ├── cli.py                 # 命令行接口
│   ├── core/
│   │   ├── checks.py         # 泄漏检测器
│   │   ├── simulator.py      # 时序模拟器
│   │   └── report.py         # 报告生成
│   └── templates/
│       └── report.html.j2    # HTML报告模板
├── examples/                 # 示例数据
│   ├── synth_train.csv      # 基础示例
│   ├── homecredit_te.csv    # 目标编码示例
│   └── fraud_rolling.csv    # 滚动统计示例
├── tests/                   # 测试用例
│   └── test_te_woe_rolling.py # 统计泄漏测试
└── runs/                    # 输出目录
```

## 🔧 检测器详解

### 1. 目标泄漏检测器
- **高相关性检测**：识别与目标高度相关的特征
- **类别纯度检测**：发现几乎完美预测目标的类别

### 2. 统计类泄漏检测器 (v0.3)
- **目标编码(TE)检测**：识别疑似目标编码特征
- **WOE检测**：识别Weight of Evidence特征
- **滚动统计检测**：识别可能跨越未来时点的滚动统计
- **聚合痕迹检测**：识别疑似聚合统计特征

### 3. 时序模拟器 (v0.3)
- **CV对比**：TimeSeriesSplit vs KFold的AUC差异
- **泄漏识别**：基于阈值判断是否存在泄漏
- **风险分级**：High/Medium/Low风险等级

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
        "name": "Target Encoding leakage risk",
        "severity": "high",
        "leak_score": 0.85,
        "evidence": {
          "suspicious_columns": {
            "target_enc_feature": {
              "correlation": 0.92,
              "leak_score": 0.85
            }
          }
        }
      }
    ],
    "simulation": {
      "summary": {
        "total_features": 2,
        "leak_features": 1,
        "leak_rate": 0.5
      }
    }
  }
}
```

### HTML报告特性
- **修复建议摘要**：按严重程度分类的修复建议
- **Statistical Leakage板块**：专门的统计类泄漏检测结果
- **时序模拟结果**：CV对比表格和摘要统计
- **风险分显示**：每个风险项的可量化风险分
- **可折叠证据**：详细的检测证据和修复建议

## 🧪 测试

```bash
# 运行所有测试
pytest -q

# 运行特定测试
pytest tests/test_te_woe_rolling.py -v

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/test
```

## 📋 版本历史

### v0.3.0 (当前)
- ✨ 新增统计类泄漏检测器（TE/WOE/滚动统计/聚合痕迹）
- ✨ 新增时序模拟器对比验证功能
- ✨ 新增风险分(leak_score)量化评估
- ✨ 新增CLI参数：--simulate-cv, --leak-threshold
- ✨ 升级报告模板：Statistical Leakage板块
- ✨ 新增示例数据：homecredit_te.csv, fraud_rolling.csv
- ✨ 新增测试用例：test_te_woe_rolling.py

### v0.2.0
- ✨ 扩展检测规则框架
- ✨ 新增JSON schema和退出码约定
- ✨ 新增统计类泄漏预览板块

### v0.1.0
- 🎉 初始版本发布
- ✨ 基础泄漏检测功能
- ✨ HTML报告生成
- ✨ 修复脚本生成

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

**Leakage Buster** - 让数据泄漏无处遁形！🕵️‍♂️
