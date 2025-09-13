
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .fix_plan import FixPlan, FixAction, FixResult

def apply_fixes(df: pd.DataFrame, fix_plan: FixPlan, target: str, time_col: Optional[str] = None) -> FixResult:
    """应用修复计划到数据框"""
    df_fixed = df.copy()
    removed_columns = []
    fixed_columns = []
    warnings = []
    recommended_cv = None
    recommended_groups = []
    
    try:
        for action in fix_plan.actions:
            if action.action_type == "delete":
                if action.target in df_fixed.columns:
                    df_fixed = df_fixed.drop(columns=[action.target])
                    removed_columns.append(action.target)
                else:
                    warnings.append(f"列 {action.target} 不存在，跳过删除")
            
            elif action.action_type == "recalculate":
                if action.target in df_fixed.columns:
                    # 这里只是标记需要重算，实际重算需要用户自己实现
                    fixed_columns.append(action.target)
                    warnings.append(f"列 {action.target} 需要重算，请参考修复建议")
                else:
                    warnings.append(f"列 {action.target} 不存在，跳过重算")
            
            elif action.action_type == "recommend_cv":
                recommended_cv = action.target
            
            elif action.action_type == "recommend_groups":
                recommended_groups = action.target.split(",")
        
        return FixResult(
            success=True,
            message=f"成功应用 {len(fix_plan.actions)} 个修复动作",
            fixed_columns=fixed_columns,
            removed_columns=removed_columns,
            recommended_cv=recommended_cv,
            recommended_groups=recommended_groups,
            warnings=warnings
        )
    
    except Exception as e:
        return FixResult(
            success=False,
            message=f"应用修复时出错: {str(e)}",
            fixed_columns=fixed_columns,
            removed_columns=removed_columns,
            recommended_cv=recommended_cv,
            recommended_groups=recommended_groups,
            warnings=warnings + [f"错误: {str(e)}"]
        )

def apply_minimal_fixes(df: pd.DataFrame, risks: List[Dict], target: str, time_col: Optional[str] = None) -> Tuple[pd.DataFrame, FixResult]:
    """应用最小可行修复（仅删除高危泄漏列）"""
    df_fixed = df.copy()
    removed_columns = []
    warnings = []
    
    # 只处理高危风险
    high_risk_actions = []
    for risk in risks:
        if risk.get("severity") == "high":
            risk_name = risk["name"]
            evidence = risk.get("evidence", {})
            
            if risk_name.startswith("Target leakage (high correlation)"):
                columns = list(evidence.get("columns", {}).keys())
                for col in columns:
                    if col in df_fixed.columns:
                        df_fixed = df_fixed.drop(columns=[col])
                        removed_columns.append(col)
                    else:
                        warnings.append(f"列 {col} 不存在，跳过删除")
    
    return df_fixed, FixResult(
        success=True,
        message=f"最小修复完成，删除了 {len(removed_columns)} 个高危泄漏列",
        fixed_columns=[],
        removed_columns=removed_columns,
        recommended_cv=None,
        recommended_groups=[],
        warnings=warnings
    )

def generate_fix_script(fix_plan: FixPlan, output_path: str) -> str:
    """生成修复脚本"""
    import os
    from datetime import datetime
    
    script_lines = [
        "#!/usr/bin/env python3",
        '"""',
        "Leakage Buster 自动修复脚本",
        f"生成时间: {datetime.now().isoformat()}",
        f"修复计划ID: {fix_plan.plan_id}",
        '"""',
        "",
        "import pandas as pd",
        "import numpy as np",
        "from sklearn.model_selection import GroupKFold, TimeSeriesSplit, KFold",
        "",
        "def apply_leakage_fixes(df: pd.DataFrame, target: str, time_col: str = None):",
        "    \"\"\"应用泄漏修复\"\"\"",
        "    df_fixed = df.copy()",
        "    removed_cols = []",
        "    recalc_cols = []",
        "",
        "    # 修复动作",
    ]
    
    for action in fix_plan.actions:
        if action.action_type == "delete":
            script_lines.extend([
                f"    # 删除高危泄漏列: {action.target}",
                f"    if '{action.target}' in df_fixed.columns:",
                f"        df_fixed = df_fixed.drop(columns=['{action.target}'])",
                f"        removed_cols.append('{action.target}')",
                f"        print(f'删除高危泄漏列: {action.target}')",
                ""
            ])
        elif action.action_type == "recalculate":
            script_lines.extend([
                f"    # 重算特征: {action.target}",
                f"    if '{action.target}' in df_fixed.columns:",
                f"        # TODO: 实现 {action.target} 的CV内重算逻辑",
                f"        recalc_cols.append('{action.target}')",
                f"        print(f'需要重算特征: {action.target}')",
                ""
            ])
    
    # 添加CV推荐
    cv_actions = [a for a in fix_plan.actions if a.action_type == "recommend_cv"]
    if cv_actions:
        cv_type = cv_actions[0].target
        script_lines.extend([
            "    # CV策略推荐",
            f"    recommended_cv = '{cv_type}'",
            "    print(f'推荐CV策略: {recommended_cv}')",
            ""
        ])
    
    # 添加分组推荐
    group_actions = [a for a in fix_plan.actions if a.action_type == "recommend_groups"]
    if group_actions:
        groups = group_actions[0].target.split(",")
        script_lines.extend([
            "    # 分组列推荐",
            f"    recommended_groups = {groups}",
            "    print(f'推荐分组列: {recommended_groups}')",
            ""
        ])
    
    script_lines.extend([
        "    return df_fixed, removed_cols, recalc_cols",
        "",
        "def get_recommended_cv_splitter(df: pd.DataFrame, target: str, time_col: str = None):",
        "    \"\"\"获取推荐的CV分割器\"\"\"",
        "    if time_col and time_col in df.columns:",
        "        return TimeSeriesSplit(n_splits=5)",
        "    elif 'recommended_groups' in locals() and recommended_groups:",
        "        return GroupKFold(n_splits=5)",
        "    else:",
        "        return KFold(n_splits=5, shuffle=True, random_state=42)",
        "",
        "if __name__ == '__main__':",
        "    # 示例用法",
        "    # df = pd.read_csv('your_data.csv')",
        "    # df_fixed, removed, recalc = apply_leakage_fixes(df, 'target_column')",
        "    # cv_splitter = get_recommended_cv_splitter(df, 'target_column')",
        "    pass"
    ])
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\\n".join(script_lines))
    
    return output_path

