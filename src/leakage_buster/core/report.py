
import os, json, datetime as dt
from typing import Dict, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

def render_report(results: Dict, meta: Dict, out_dir: str, simulation_results: Optional[Dict] = None, policy_audit: Optional[Dict] = None):
    env = Environment(loader=FileSystemLoader(searchpath=os.path.join(os.path.dirname(__file__), "..", "templates")),
                      autoescape=select_autoescape())
    tpl = env.get_template("report.html.j2")
    html = tpl.render(
        results=results, 
        meta=meta, 
        simulation=simulation_results,
        policy_audit=policy_audit,
        now=dt.datetime.now().isoformat(timespec="seconds")
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path

def write_fix_script(results: Dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "fix_transforms.py")
    suggestions = []
    drop_cols = []
    group_cols = []
    te_cols = []
    window_cols = []
    
    for r in results.get("risks", []):
        risk_name = r["name"]
        evidence = r.get("evidence", {})
        
        if risk_name.startswith("Target leakage (high correlation)"):
            cols = list(evidence.get("columns", {}).keys())
            drop_cols.extend(cols)
            suggestions.append(f"# 高危：删除高相关泄漏列：{cols}")
            
        elif risk_name.startswith("Target encoding leakage"):
            cols = list(evidence.get("columns", {}).keys())
            te_cols.extend(cols)
            suggestions.append(f"# 高危：疑似目标编码泄漏列：{cols}")
            suggestions.append("# 建议：检查是否使用全量目标编码，改为CV内编码")
            
        elif risk_name.startswith("Time window leakage"):
            cols = list(evidence.get("columns", {}).keys())
            window_cols.extend(cols)
            suggestions.append(f"# 高危：疑似全量统计泄漏列：{cols}")
            suggestions.append("# 建议：改为仅使用窗口内可见数据的统计")
            
        elif risk_name.startswith("Target leakage (categorical purity)"):
            cols = list(evidence.get("columns", {}).keys())
            suggestions.append(f"# 中危：类别纯度异常列：{cols}")
            suggestions.append("# 建议：检查是否由目标聚合产生，考虑删除或重算")
            
        elif risk_name.startswith("KFold leakage risk"):
            candidates = evidence.get("candidates", [])
            group_cols.extend([c["column"] for c in candidates])
            suggestions.append(f"# 中危：建议使用GroupKFold的列：{[c['column'] for c in candidates]}")
            
        elif risk_name.startswith("Time-awareness suggestion"):
            suggestions.append("# 低危：建议使用时间感知的特征工程和验证策略")
            
        elif risk_name.startswith("CV strategy"):
            suggestions.append("# 建议：检查CV策略是否适合数据特征")
    
    # 生成修复脚本
    script_lines = [
        "#!/usr/bin/env python3",
        '"""',
        "Leakage Buster 修复建议脚本",
        "自动生成于: " + dt.datetime.now().isoformat(),
        '"""',
        "",
        "import pandas as pd",
        "import numpy as np",
        "from sklearn.model_selection import GroupKFold, TimeSeriesSplit",
        "",
        "def apply_fixes(df: pd.DataFrame, target: str, time_col: str = None):",
        "    \"\"\"应用修复建议\"\"\"",
        "    df_fixed = df.copy()",
        "",
        "    # 1. 删除高危泄漏列",
        f"    drop_cols = {drop_cols}",
        "    if drop_cols:",
        "        print(f'删除高危泄漏列: {drop_cols}')",
        "        df_fixed = df_fixed.drop(columns=drop_cols)",
        "",
        "    # 2. 处理目标编码特征",
        f"    te_cols = {te_cols}",
        "    if te_cols:",
        "        print(f'发现疑似目标编码特征: {te_cols}')",
        "        print('建议：在CV内重新计算目标编码，避免使用全量数据')",
        "",
        "    # 3. 处理时间窗口特征",
        f"    window_cols = {window_cols}",
        "    if window_cols:",
        "        print(f'发现疑似全量统计特征: {window_cols}')",
        "        print('建议：改为仅使用历史窗口数据的统计')",
        "",
        "    # 4. 分组列建议",
        f"    group_cols = {group_cols}",
        "    if group_cols:",
        "        print(f'建议使用GroupKFold的列: {group_cols}')",
        "",
        "    return df_fixed",
        "",
        "def get_recommended_cv_splitter(df: pd.DataFrame, target: str, time_col: str = None):",
        "    \"\"\"获取推荐的CV分割器\"\"\"",
        "    if time_col and time_col in df.columns:",
        "        return TimeSeriesSplit(n_splits=5)",
        "    elif group_cols:",
        "        return GroupKFold(n_splits=5)",
        "    else:",
        "        from sklearn.model_selection import KFold",
        "        return KFold(n_splits=5, shuffle=True, random_state=42)",
        "",
        "if __name__ == '__main__':",
        "    # 示例用法",
        "    # df = pd.read_csv('your_data.csv')",
        "    # df_fixed = apply_fixes(df, 'target_column')",
        "    # cv_splitter = get_recommended_cv_splitter(df, 'target_column')",
        "    pass"
    ]
    
    with open(path, "w", encoding="utf-8") as f:
        f.write("\\n".join(script_lines))
    return path

def write_meta(meta: Dict, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return path

def get_fix_summary(results: Dict) -> Dict:
    """提取修复建议摘要"""
    risks = results.get("risks", [])
    high_risks = [r for r in risks if r.get("severity") == "high"]
    medium_risks = [r for r in risks if r.get("severity") == "medium"]
    low_risks = [r for r in risks if r.get("severity") == "low"]
    
    return {
        "high": len(high_risks),
        "medium": len(medium_risks),
        "low": len(low_risks),
        "total": len(risks)
    }

