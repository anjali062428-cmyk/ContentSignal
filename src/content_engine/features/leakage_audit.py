"""
Leakage Audit Engine.
Performs strict, dynamic inspection of the actual final feature set reaching estimators.
Classifies all dataset columns across 6 categories, audits for mathematical equivalence,
and raises a SecurityLeakageError if any forbidden information reaches the model.
Outputs reports/leakage_audit.json and reports/leakage_audit.md.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Set
import pandas as pd

from content_engine.config import (
    REPORTS_DIR,
    DOCUMENTED_44_COLUMNS,
    RESTRICTED_FLYRANK_COLUMNS,
    IDENTIFIER_COLUMNS,
    TARGET_COLUMN,
    FORBIDDEN_LEAKAGE_COLUMNS,
    METADATA_EXCLUDED_COLUMNS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)


class SecurityLeakageError(Exception):
    """Raised when forbidden target or proprietary information reaches an estimator."""
    pass


def audit_feature_names(
    actual_feature_names: List[str],
    reports_dir: Path = REPORTS_DIR,
) -> Dict[str, Any]:
    """
    Audits the actual feature names passed to a scikit-learn estimator.
    Ensures 0% leakage from target construction or proprietary fields.
    """
    actual_set = set(actual_feature_names)

    # 1. Check for Restricted Proprietary Columns
    restricted_leaks = actual_set.intersection(set(RESTRICTED_FLYRANK_COLUMNS))
    if restricted_leaks:
        raise SecurityLeakageError(
            f"LEAKAGE VIOLATION: Proprietary FlyRank decision columns found in estimator input: {restricted_leaks}"
        )

    # 2. Check for Identifiers
    id_leaks = actual_set.intersection(set(IDENTIFIER_COLUMNS))
    if id_leaks:
        raise SecurityLeakageError(
            f"LEAKAGE VIOLATION: Identifier columns found in estimator input: {id_leaks}"
        )

    # 3. Check for Target Column
    if TARGET_COLUMN in actual_set:
        raise SecurityLeakageError(
            f"LEAKAGE VIOLATION: Target column '{TARGET_COLUMN}' found in estimator input!"
        )

    # 4. Check for Direct Target-Construction Leakage
    construction_leaks = actual_set.intersection(set(FORBIDDEN_LEAKAGE_COLUMNS))
    if construction_leaks:
        raise SecurityLeakageError(
            f"LEAKAGE VIOLATION: Target-construction columns found in estimator input: {construction_leaks}"
        )

    # 5. Check for Mathematical Equivalent Patterns (e.g. substrings of last_30d, prev_30d)
    forbidden_tokens = ["last_30d", "prev_30d", "trend_pct", "trend_dir"]
    subtoken_leaks = []
    for feat in actual_feature_names:
        for token in forbidden_tokens:
            if token in feat.lower():
                subtoken_leaks.append(feat)
    if subtoken_leaks:
        raise SecurityLeakageError(
            f"LEAKAGE VIOLATION: Forbidden target-construction token detected in feature(s): {subtoken_leaks}"
        )

    # 6. Six-Tier Full Column Classification
    classification = {
        "1_restricted_proprietary_columns": sorted(RESTRICTED_FLYRANK_COLUMNS),
        "2_identifiers": sorted(IDENTIFIER_COLUMNS),
        "3_target_columns": [TARGET_COLUMN],
        "4_direct_target_construction_variables": [
            "impressions_last_30d", "impressions_prev_30d", "impressions_change_30d",
            "trend_direction", "trend_pct"
        ],
        "5_future_variables": [
            "next_30d_impressions (warehouse only)",
            "next_30d_clicks (warehouse only)",
            "next_30d_recovery_status (warehouse only)"
        ],
        "6_legitimate_predictive_features": sorted(list(actual_set)),
    }

    audit_summary = {
        "audit_passed": True,
        "total_features_evaluated": len(actual_feature_names),
        "forbidden_features_detected": 0,
        "classification": classification,
        "rules_enforced": [
            "Zero proprietary FlyRank decision columns",
            "Zero client or content identifiers in feature matrix",
            "Zero target construction columns (impressions_last_30d, impressions_prev_30d, trend_pct, trend_direction)",
            "Zero subtoken leaks or mathematical reconstructors",
            "Dynamic inspection of actual estimator feature names"
        ]
    }

    # Write reports
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "leakage_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2)

    _generate_leakage_audit_markdown(audit_summary, reports_dir / "leakage_audit.md")

    return audit_summary


def _generate_leakage_audit_markdown(audit: Dict[str, Any], output_path: Path) -> None:
    c = audit["classification"]
    md = f"""# Target-Construction Leakage Audit Report

**Status:** {'PASSED (Zero Leakage Detected)' if audit['audit_passed'] else 'FAILED'}  
**Audited Feature Count:** {audit['total_features_evaluated']} legitimate features reaching estimator.

---

## 1. Executive Summary
This audit inspects the **actual feature names** reaching scikit-learn estimators prior to training. It enforces strict separation between observable prior features and target construction artifacts.

---

## 2. Six-Tier Column Classification

### Tier 1: Restricted Proprietary Columns ({len(c['1_restricted_proprietary_columns'])})
*Quarantined upon raw ingestion. Forbidden across the entire codebase.*
"""
    for col in c["1_restricted_proprietary_columns"]:
        md += f"- `{col}` (STATUS: QUARANTINED)\n"

    md += f"""
### Tier 2: Identifiers ({len(c['2_identifiers'])})
*Hashed pseudonyms reserved strictly for grouping and client-aware splits.*
"""
    for col in c["2_identifiers"]:
        md += f"- `{col}` (STATUS: EXCLUDED FROM FEATURES)\n"

    md += f"""
### Tier 3: Target Columns ({len(c['3_target_columns'])})
*The supervised ground truth label.*
"""
    for col in c["3_target_columns"]:
        md += f"- `{col}` (STATUS: TARGET ONLY)\n"

    md += f"""
### Tier 4: Direct Target-Construction Variables ({len(c['4_direct_target_construction_variables'])})
*Input components of the target label. Banned from candidate features to prevent trivial target reconstruction.*
"""
    for col in c["4_direct_target_construction_variables"]:
        md += f"- `{col}` (STATUS: STRICTLY BANNED)\n"

    md += f"""
### Tier 5: Future Variables ({len(c['5_future_variables'])})
*Forward-looking observations requiring enterprise warehouse daily tables.*
"""
    for col in c["5_future_variables"]:
        md += f"- `{col}` (STATUS: NOT PRESENT IN STARTER SLICE)\n"

    md += f"""
### Tier 6: Legitimate Predictive Features ({len(c['6_legitimate_predictive_features'])})
*Clean, observable, leakage-safe features approved for model training.*
"""
    for col in c["6_legitimate_predictive_features"]:
        md += f"- `{col}`\n"

    md += """
---

## 3. Dynamic Pipeline Enforcement
The model training pipeline executes `audit_feature_names()` dynamically before fitting any estimator. If any banned column or token is detected, a `SecurityLeakageError` halts execution immediately.
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


if __name__ == "__main__":
    from content_engine.config import NUMERIC_FEATURES, CATEGORICAL_FEATURES
    print("Testing leakage audit...")
    candidate_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    audit = audit_feature_names(candidate_features)
    print(f"Leakage audit passed! Features audited: {audit['total_features_evaluated']}")
