
# Leakage Buster v0.5-rc

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

### ⏰ 时序模拟器
- **对比验证**：TimeSeriesSplit与KFold的OOF指标变化
- **泄漏阈值**：可配置的泄漏检测阈值
- **风险分级**：基于分数差异的严重程度评估
- **量化证据**：结构化的检测证据和风险分

### 🔧 半自动修复 (v0.5-rc新增)
- **修复计划**：生成结构化的修复计划JSON
- **自动应用**：基于计划自动修复数据
- **智能建议**：删除/重算/推荐CV与groups
- **证据引用**：记录来源风险与理由

### 🐍 Python SDK (v0.5-rc新增)
- **稳定API**：`audit()`, `plan_fixes()`, `apply_fixes()`
- **类型安全**：完整的类型注解和Pydantic模型
- **CI友好**：标准化的退出码和错误处理
- **文档化**：详细的API文档和示例

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
leakage-buster run --train examples/homecredit_te.csv --target y --time-col date --out runs/v05_te --simulate-cv time --leak-threshold 0.02

# 生成修复计划
leakage-buster run --train examples/homecredit_te.csv --target y --time-col date --out runs/v05_plan --auto-fix plan --fix-json runs/v05_plan/fix_plan.json

# 应用修复
leakage-buster run --train examples/homecredit_te.csv --target y --time-col date --out runs/v05_apply --auto-fix apply --fixed-train runs/v05_apply/fixed_train.csv
```

### Python SDK使用
```python
from leakage_buster.api import audit, plan_fixes, apply_fixes_to_dataframe
import pandas as pd

# 加载数据
df = pd.read_csv('your_data.csv')

# 审计数据
audit_result = audit(df, target='y', time_col='date')

# 生成修复计划
fix_plan = plan_fixes(audit_result, 'your_data.csv')

# 应用修复
fixed_df = apply_fixes_to_dataframe(df, fix_plan)

# 检查结果
print(f"检测到 {audit_result.risk_count} 个风险")
print(f"高危风险: {audit_result.high_risk_count}")
```

### 参数说明
- `--train`: 训练数据CSV文件路径
- `--target`: 目标列名
- `--time-col`: 时间列名（可选）
- `--out`: 输出目录
- `--cv-type`: CV策略（kfold/timeseries/group）
- `--simulate-cv`: 启用时序模拟（time）
- `--leak-threshold`: 泄漏阈值（默认0.02）
- `--auto-fix`: 自动修复模式（plan/apply）
- `--fix-json`: 修复计划JSON输出路径
- `--fixed-train`: 修复后数据CSV输出路径

## 📁 项目结构

```
leakage-buster/
├── src/leakage_buster/
│   ├── api.py                    # Python SDK
│   ├── cli.py                    # 命令行接口
│   ├── core/
│   │   ├── checks.py            # 泄漏检测器
│   │   ├── simulator.py         # 时序模拟器
│   │   ├── report.py            # 报告生成
│   │   ├── cv_policy.py         # CV策略审计
│   │   ├── export.py            # 导出功能
│   │   ├── fix_plan.py          # 修复计划模型
│   │   └── fix_apply.py         # 修复应用逻辑
│   └── templates/
│       └── report.html.j2       # HTML报告模板
├── examples/                     # 示例数据
│   ├── synth_train.csv          # 基础示例
│   ├── homecredit_te.csv        # 目标编码示例
│   ├── fraud_rolling.csv        # 滚动统计示例
│   └── group_cv.csv             # 分组CV示例
├── tests/                       # 测试用例
│   ├── test_smoke.py            # 冒烟测试
│   ├── test_te_woe_rolling.py   # 统计泄漏测试
│   ├── test_cv_policy.py        # CV策略测试
│   └── test_autofix.py          # 自动修复测试
├── conf/                        # 配置文件
│   └── cv_policy.yaml           # CV策略配置
├── .github/workflows/           # CI/CD配置
│   └── ci.yml                   # GitHub Actions
└── docs/versions/               # 版本文档
    ├── README_v0.1.md
    ├── README_v0.2.md
    ├── README_v0.3.md
    └── README_v0.4.md
```

## 🔧 检测器详解

### 1. 目标泄漏检测器
- **高相关性检测**：识别与目标高度相关的特征
- **类别纯度检测**：发现几乎完美预测目标的类别

### 2. 统计类泄漏检测器
- **目标编码(TE)检测**：识别疑似目标编码特征
- **WOE检测**：识别Weight of Evidence特征
- **滚动统计检测**：识别可能跨越未来时点的滚动统计
- **聚合痕迹检测**：识别疑似聚合统计特征

### 3. 时序模拟器
- **CV对比**：TimeSeriesSplit vs KFold的AUC差异
- **泄漏识别**：基于阈值判断是否存在泄漏
- **风险分级**：High/Medium/Low风险等级

### 4. 半自动修复系统 (v0.5-rc)
- **修复计划生成**：基于风险分析生成结构化修复计划
- **智能修复应用**：自动删除高危列、重算可疑特征
- **CV策略推荐**：根据数据特征推荐合适的CV策略
- **分组列建议**：识别需要GroupKFold的列

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
    "fix_plan": {
      "version": "1.0",
      "total_risks": 1,
      "high_risk_items": 1,
      "delete_columns": [],
      "recalculate_columns": [
        {
          "action": "recalculate",
          "column": "target_enc_feature",
          "reason": "目标编码泄漏：疑似使用全量数据计算",
          "confidence": 0.8
        }
      ]
    }
  }
}
```

### 退出码规范
- `0`: 成功，无风险
- `2`: 警告，有中低危风险
- `3`: 高危泄漏，需要立即处理
- `4`: 配置错误，无法执行

### 修复计划JSON
```json
{
  "version": "1.0",
  "total_risks": 3,
  "high_risk_items": 1,
  "medium_risk_items": 1,
  "low_risk_items": 1,
  "delete_columns": [
    {
      "action": "delete",
      "column": "leak_col",
      "reason": "高相关性泄漏：与目标相关性过高",
      "confidence": 0.9
    }
  ],
  "recalculate_columns": [
    {
      "action": "recalculate",
      "column": "target_enc_feature",
      "reason": "目标编码泄漏：疑似使用全量数据计算",
      "confidence": 0.8
    }
  ],
  "cv_recommendations": [
    {
      "action": "recommend_cv",
      "column": "",
      "reason": "CV策略推荐：timeseries",
      "confidence": 0.6
    }
  ],
  "group_recommendations": [
    {
      "action": "recommend_groups",
      "column": "user_id",
      "reason": "分组泄漏风险：高重复率列",
      "confidence": 0.7
    }
  ]
}
```

## 🧪 测试

```bash
# 运行所有测试
pytest -q

# 运行特定测试
pytest tests/test_autofix.py -v

# 运行示例
leakage-buster run --train examples/synth_train.csv --target y --time-col date --out runs/test
```

## 🔄 CI/CD集成

### GitHub Actions示例
```yaml
- name: Run leakage audit
  run: |
    leakage-buster run --train data/train.csv --target y --time-col date --out runs/audit
    if [ $? -eq 3 ]; then
      echo "❌ High leakage detected! Build failed."
      exit 1
    fi
```

### 退出码处理
```bash
# 检查退出码
leakage-buster run --train data.csv --target y --out runs/audit
case $? in
  0) echo "✅ No issues found" ;;
  2) echo "⚠️  Warnings found" ;;
  3) echo "❌ High leakage detected!" ;;
  4) echo "💥 Configuration error" ;;
esac
```

## 📋 版本历史

### v0.5-rc (当前)
- ✨ 新增半自动修复系统（plan/apply模式）
- ✨ 新增稳定的Python SDK API
- ✨ 新增标准化的退出码规范
- ✨ 新增CI/CD集成示例
- ✨ 新增Pydantic模型和类型安全
- ✨ 新增修复计划JSON格式
- ✨ 新增GitHub Actions CI配置

### v0.4.0
- ✨ 口径一致性审计功能
- ✨ PDF和SARIF导出功能
- ✨ 升级报告模板（目录、风险矩阵）
- ✨ 新增CV策略配置文件

### v0.3.0
- ✨ 统计类泄漏检测器
- ✨ 时序模拟器对比验证
- ✨ 风险分量化评估

### v0.2.0
- ✨ 扩展检测规则框架
- ✨ JSON schema和退出码约定

### v0.1.0
- 🎉 初始版本发布
- ✨ 基础泄漏检测功能

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

---

**Leakage Buster** - 让数据泄漏无处遁形！🕵️‍♂️
