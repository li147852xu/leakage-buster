
from __future__ import annotations
import os
import json
import subprocess
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import pandas as pd

@dataclass
class SARIFResult:
    """SARIF结果项"""
    rule_id: str
    level: str  # error, warning, note
    message: str
    locations: List[Dict]
    properties: Dict

class ReportExporter:
    """报告导出器"""
    
    def __init__(self):
        self.weasyprint_available = self._check_weasyprint()
    
    def _check_weasyprint(self) -> bool:
        """检查weasyprint是否可用"""
        try:
            import weasyprint
            return True
        except ImportError:
            return False
    
    def export_pdf(self, html_file: str, output_file: str) -> Dict:
        """导出PDF报告"""
        if not os.path.exists(html_file):
            return {
                "status": "error",
                "message": f"HTML file not found: {html_file}",
                "fallback": None
            }
        
        if self.weasyprint_available:
            try:
                import weasyprint
                weasyprint.HTML(filename=html_file).write_pdf(output_file)
                return {
                    "status": "success",
                    "message": "PDF exported successfully",
                    "output_file": output_file,
                    "method": "weasyprint"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"WeasyPrint error: {str(e)}",
                    "fallback": "html"
                }
        else:
            return {
                "status": "fallback",
                "message": "WeasyPrint not available, falling back to HTML",
                "output_file": html_file,
                "method": "html",
                "install_hint": "pip install 'leakage-buster[pdf]'"
            }
    
    def export_sarif(self, results: Dict, output_file: str) -> Dict:
        """导出SARIF格式报告"""
        try:
            sarif_data = self._convert_to_sarif(results)
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sarif_data, f, ensure_ascii=False, indent=2)
            
            return {
                "status": "success",
                "message": "SARIF exported successfully",
                "output_file": output_file,
                "results_count": len(sarif_data.get("runs", [{}])[0].get("results", []))
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"SARIF export error: {str(e)}",
                "output_file": None
            }
    
    def _convert_to_sarif(self, results: Dict) -> Dict:
        """将检测结果转换为SARIF格式"""
        risks = results.get("risks", [])
        sarif_results = []
        
        for risk in risks:
            sarif_result = self._risk_to_sarif(risk)
            if sarif_result:
                sarif_results.append(sarif_result)
        
        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Leakage Buster",
                            "version": "0.4.0",
                            "informationUri": "https://github.com/li147852xu/leakage-buster",
                            "rules": self._get_sarif_rules()
                        }
                    },
                    "results": sarif_results
                }
            ]
        }
    
    def _risk_to_sarif(self, risk: Dict) -> Optional[Dict]:
        """将风险项转换为SARIF结果"""
        severity = risk.get("severity", "medium")
        name = risk.get("name", "Unknown risk")
        detail = risk.get("detail", "")
        evidence = risk.get("evidence", {})
        
        # 映射严重程度到SARIF级别
        level_map = {
            "high": "error",
            "medium": "warning", 
            "low": "note"
        }
        level = level_map.get(severity, "warning")
        
        # 生成规则ID
        rule_id = self._generate_rule_id(name)
        
        # 生成位置信息
        locations = self._generate_locations(evidence)
        
        # 生成消息
        message = {
            "text": f"{name}: {detail}"
        }
        
        # 生成属性
        properties = {
            "leak_score": risk.get("leak_score", 0.0),
            "evidence": evidence
        }
        
        return {
            "ruleId": rule_id,
            "level": level,
            "message": message,
            "locations": locations,
            "properties": properties
        }
    
    def _generate_rule_id(self, risk_name: str) -> str:
        """生成规则ID"""
        # 将风险名称转换为规则ID
        rule_id = risk_name.lower()
        rule_id = rule_id.replace(" ", "_")
        rule_id = rule_id.replace("(", "")
        rule_id = rule_id.replace(")", "")
        rule_id = rule_id.replace(":", "")
        return f"leakage_buster_{rule_id}"
    
    def _generate_locations(self, evidence: Dict) -> List[Dict]:
        """生成位置信息"""
        locations = []
        
        # 如果有可疑列信息，生成位置
        if "suspicious_columns" in evidence:
            for col_name in evidence["suspicious_columns"].keys():
                locations.append({
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": "data.csv"
                        },
                        "region": {
                            "startLine": 1,
                            "endLine": 1,
                            "startColumn": 1,
                            "endColumn": 1
                        }
                    },
                    "logicalLocations": [
                        {
                            "name": col_name,
                            "kind": "column"
                        }
                    ]
                })
        
        # 如果没有具体位置，生成通用位置
        if not locations:
            locations.append({
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": "data.csv"
                    }
                }
            })
        
        return locations
    
    def _get_sarif_rules(self) -> List[Dict]:
        """获取SARIF规则定义"""
        return [
            {
                "id": "leakage_buster_target_leakage_high_correlation",
                "name": "Target Leakage (High Correlation)",
                "shortDescription": {
                    "text": "Feature has high correlation with target"
                },
                "fullDescription": {
                    "text": "This feature has a very high correlation (|corr| or R² ≥ 0.98) with the target variable, which may indicate data leakage."
                },
                "help": {
                    "text": "Consider removing this feature or recalculating it within CV folds to avoid leakage."
                },
                "properties": {
                    "tags": ["leakage", "correlation", "high-severity"]
                }
            },
            {
                "id": "leakage_buster_target_encoding_leakage_risk",
                "name": "Target Encoding Leakage Risk",
                "shortDescription": {
                    "text": "Suspected target encoding feature"
                },
                "fullDescription": {
                    "text": "This feature appears to be target encoded and may have been calculated using the full dataset, causing leakage."
                },
                "help": {
                    "text": "Ensure target encoding is calculated only within CV folds to prevent leakage."
                },
                "properties": {
                    "tags": ["leakage", "target-encoding", "medium-severity"]
                }
            },
            {
                "id": "leakage_buster_woe_leakage_risk",
                "name": "WOE Leakage Risk",
                "shortDescription": {
                    "text": "Suspected WOE feature"
                },
                "fullDescription": {
                    "text": "This feature appears to be Weight of Evidence (WOE) encoded and may have been calculated using the full dataset."
                },
                "help": {
                    "text": "Ensure WOE calculation is done only within CV folds to prevent leakage."
                },
                "properties": {
                    "tags": ["leakage", "woe", "medium-severity"]
                }
            },
            {
                "id": "leakage_buster_rolling_statistics_leakage_risk",
                "name": "Rolling Statistics Leakage Risk",
                "shortDescription": {
                    "text": "Suspected rolling statistics feature"
                },
                "fullDescription": {
                    "text": "This feature appears to be a rolling statistic that may have used future information."
                },
                "help": {
                    "text": "Ensure rolling statistics only use historical data within the time window."
                },
                "properties": {
                    "tags": ["leakage", "rolling-statistics", "high-severity"]
                }
            },
            {
                "id": "leakage_buster_kfold_leakage_risk",
                "name": "KFold Leakage Risk",
                "shortDescription": {
                    "text": "High duplicate columns detected"
                },
                "fullDescription": {
                    "text": "These columns have high duplication rates and should be used as groups in GroupKFold to avoid cross-fold leakage."
                },
                "help": {
                    "text": "Consider using GroupKFold with these columns as group identifiers."
                },
                "properties": {
                    "tags": ["leakage", "kfold", "medium-severity"]
                }
            },
            {
                "id": "leakage_buster_cv_policy_violation",
                "name": "CV Policy Violation",
                "shortDescription": {
                    "text": "CV strategy mismatch with policy"
                },
                "fullDescription": {
                    "text": "The current CV strategy does not match the configured policy, which may lead to inconsistent evaluation."
                },
                "help": {
                    "text": "Update CV strategy to match policy or update policy to match data characteristics."
                },
                "properties": {
                    "tags": ["policy", "cv-strategy", "medium-severity"]
                }
            }
        ]

def export_report(html_file: str, output_file: str, export_type: str, results: Optional[Dict] = None) -> Dict:
    """导出报告的便捷函数"""
    exporter = ReportExporter()
    
    if export_type == "pdf":
        return exporter.export_pdf(html_file, output_file)
    elif export_type == "sarif":
        if not results:
            return {
                "status": "error",
                "message": "SARIF export requires results data"
            }
        return exporter.export_sarif(results, output_file)
    else:
        return {
            "status": "error",
            "message": f"Unsupported export type: {export_type}"
        }

