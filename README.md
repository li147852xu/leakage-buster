# Leakage Buster

[![PyPI version](https://img.shields.io/pypi/v/leakage-buster.svg)](https://pypi.org/project/leakage-buster/)
[![Python](https://img.shields.io/pypi/pyversions/leakage-buster.svg)](https://pypi.org/project/leakage-buster/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/li147852xu/leakage-buster/actions/workflows/ci.yml/badge.svg)](https://github.com/li147852xu/leakage-buster/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/li147852xu/leakage-buster/branch/main/graph/badge.svg)](https://codecov.io/gh/li147852xu/leakage-buster)

> 专业的**时间泄漏 / KFold 泄漏 / 口径一致性审计**工具，提供报告与修复建议，支持 CLI 与 Python SDK。

## 这是什么 & 解决什么问题
- **为什么需要**：在表格建模中，目标编码、滚动统计或错误的折法会"看未来"，使 OOF 虚高，线上掉崖。
- **它做了什么**：
  - 检测：高相关/分类纯度、TE/WOE/滚动统计泄漏、KFold/Group 泄漏、时间列问题、口径一致性。
  - 评估：时序模拟（TimeSeriesSplit vs KFold）对比，量化泄漏影响。
  - 修复：输出修复脚本/计划（删列/折内重算/推荐分组），可一键 `apply`。
  - 交付：HTML/PDF 报告、SARIF 告警、Docker & PyPI、一键复现 `meta.json`。
- **适用场景**：金融风控/欺诈、时序二分类/回归、比赛/生产前审计。

## 三分钟上手
```bash
pip install leakage-buster

leakage-buster run \
  --train examples/synth_train.csv \
  --target y --time-col date \
  --out runs/demo
```

**CLI 关键参数**
- `--simulate-cv time`：启用时序模拟；`--leak-threshold` 控制标红阈值
- `--cv-policy-file`：校验离线/在线口径一致性
- `--auto-fix plan|apply`：生成/应用修复计划
- `--export pdf|sarif`：导出 PDF/SARIF

## ✨ 核心特性

### 🔍 全面检测能力
- **目标泄漏检测**：高相关性（|corr|/R²≥0.98）、类别纯度异常
- **统计类泄漏检测**：目标编码(TE)、WOE、滚动统计、聚合痕迹
- **时间泄漏检测**：时间列解析、时间感知建议
- **分组泄漏检测**：高重复列→GroupKFold建议
- **CV策略一致性**：TimeSeriesSplit vs KFold vs GroupKFold推荐
- **口径一致性审计**：离线/在线口径差异检测

### ⚡ 高性能处理
- **多引擎支持**：pandas（默认）、polars（可选）
- **并行处理**：多核并行检测，支持`--n-jobs`参数
- **内存控制**：智能内存管理，支持`--memory-cap`限制
- **大数据支持**：分块处理、采样策略，支持百万行数据
- **性能优化**：自动数据类型优化，减少内存占用

### 🔧 半自动修复
- **修复计划生成**：结构化的修复建议JSON
- **自动修复应用**：基于计划自动修复数据
- **智能建议**：删除/重算/推荐CV与groups
- **证据引用**：记录来源风险与理由

### 📊 专业报告
- **交互式报告**：风险雷达图、风险矩阵、可折叠证据
- **多格式导出**：HTML、PDF、SARIF（GitHub Code Scanning）
- **详细元数据**：Git hash、随机种子、系统信息
- **响应式设计**：支持移动端和打印

### 🐍 稳定SDK
- **Python API**：`audit()`, `plan_fixes()`, `apply_fixes()`
- **类型安全**：完整的类型注解和Pydantic模型
- **CI友好**：标准化的退出码和错误处理
- **文档完整**：详细的API文档和示例

## 📋 完整参数表

### 基础参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--train` | str | 必需 | 训练数据CSV文件路径 |
| `--target` | str | 必需 | 目标列名 |
| `--time-col` | str | None | 时间列名（可选） |
| `--out` | str | 必需 | 输出目录 |

### CV策略参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--cv-type` | str | None | CV策略：kfold/timeseries/group |
| `--simulate-cv` | str | None | 启用时序模拟：time |
| `--leak-threshold` | float | 0.02 | 泄漏阈值 |
| `--cv-policy-file` | str | None | CV策略配置文件（YAML） |

### 性能参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--engine` | str | pandas | 数据处理引擎：pandas/polars |
| `--n-jobs` | int | -1 | 并行作业数（-1=自动） |
| `--memory-cap` | int | 4096 | 内存限制（MB） |
| `--sample-ratio` | float | None | 大数据集采样比例（0.0-1.0） |

### 导出参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--export` | str | None | 导出格式：pdf |
| `--export-sarif` | str | None | SARIF文件路径（GitHub Code Scanning） |

### 自动修复参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--auto-fix` | str | None | 自动修复模式：plan/apply |
| `--fix-json` | str | None | 修复计划JSON输出路径 |
| `--fixed-train` | str | None | 修复后数据CSV输出路径 |

## 🐳 Docker使用

### 构建镜像
```bash
docker build -t leakage-buster .
```

### 运行容器
```bash
# 基本使用
docker run -v $(pwd):/data leakage-buster run --train /data/data.csv --target y --out /data/output

# 高性能使用
docker run -v $(pwd):/data leakage-buster run --train /data/data.csv --target y --out /data/output \
  --engine pandas --n-jobs 8 --memory-cap 4096
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

### 退出码规范
- **0**: 成功，无风险
- **2**: 警告，有中低危风险
- **3**: 高危泄漏，需要立即处理
- **4**: 配置错误，无法执行

## 📊 性能基准

### 测试环境
- **CPU**: 8核 Intel i7
- **内存**: 16GB RAM
- **数据**: 150K行 × 250列

### 性能指标
| 指标 | pandas | polars | 提升 |
|------|--------|--------|------|
| 加载时间 | 15.2s | 8.7s | 1.7x |
| 审计时间 | 45.3s | 28.1s | 1.6x |
| 内存使用 | 2.1GB | 1.4GB | 1.5x |
| 并行效率 | 6.2x | 7.8x | 1.3x |

## 🔗 与tabular-agent集成

### 在tabular-agent中调用
```python
# 在tabular-agent的audit子命令中
from leakage_buster.api import audit, plan_fixes

def audit_data(data_path, target_col, time_col=None):
    df = pd.read_csv(data_path)
    audit_result = audit(df, target=target_col, time_col=time_col)
    fix_plan = plan_fixes(audit_result, data_path)
    
    return {
        "risks": audit_result.risks,
        "fix_plan": fix_plan.model_dump(),
        "exit_code": 3 if audit_result.has_high_risk else 2 if audit_result.has_medium_risk else 0
    }
```

### JSON Schema
```json
{
  "status": "success",
  "exit_code": 0,
  "data": {
    "risks": [...],
    "fix_plan": {...},
    "summary": {...}
  }
}
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest -q

# 运行性能测试
pytest tests/perf/test_perf_medium.py -k perf -s

# 跳过慢测试
pytest -q -k "not slow"
```

### 测试覆盖
- **单元测试**: 100% 核心功能覆盖
- **集成测试**: CLI和API端到端测试
- **性能测试**: 中等规模数据集测试
- **安全测试**: Bandit和Safety扫描

## 📈 版本历史

### v1.0.1 (当前)
- 🔧 修复CI测试失败问题
- 🔧 清理GitHub上的debug文件
- ✨ 添加PyPI发布支持
- ✨ 添加Codecov覆盖率支持
- 🔧 修复README徽章链接

### v1.0.0
- ✨ 性能与容错：pandas/polars引擎、并行处理、内存控制
- ✨ 专业报告：风险雷达图、交互式界面、多格式导出
- ✨ Docker支持：轻量镜像、健康检查、完整元数据
- ✨ PyPI就绪：完整元数据、可选依赖、测试配置

### v0.5-rc
- ✨ 半自动修复系统
- ✨ 稳定Python SDK
- ✨ 标准化退出码

### v0.4.0
- ✨ 口径一致性审计
- ✨ PDF/SARIF导出
- ✨ 升级报告模板

### v0.3.0
- ✨ 统计类泄漏检测
- ✨ 时序模拟器
- ✨ 风险分量化

### v0.2.0
- ✨ 扩展检测框架
- ✨ JSON schema约定

### v0.1.0
- 🎉 初始版本发布

## 🤝 贡献

我们欢迎各种形式的贡献！

### 贡献方式
1. **报告问题**: [GitHub Issues](https://github.com/li147852xu/leakage-buster/issues)
2. **功能请求**: [GitHub Discussions](https://github.com/li147852xu/leakage-buster/discussions)
3. **代码贡献**: Fork → 开发 → Pull Request
4. **文档改进**: 直接编辑或提交PR

### 开发环境
```bash
git clone https://github.com/li147852xu/leakage-buster.git
cd leakage-buster
pip install -e ".[dev]"
pytest
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢所有贡献者和用户的支持！

---

**Leakage Buster** - 让数据泄漏无处遁形！🕵️‍♂️

[![Star](https://img.shields.io/github/stars/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)
[![Fork](https://img.shields.io/github/forks/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)
[![Watch](https://img.shields.io/github/watchers/li147852xu/leakage-buster?style=social)](https://github.com/li147852xu/leakage-buster)