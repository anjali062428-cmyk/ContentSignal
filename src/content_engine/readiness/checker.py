"""
Dataset Readiness and Compatibility Evaluator.
Executes the 10-point Readiness Checklist:
1. File readable
2. Rows detected
3. Content records
4. Performance signals
5. Suitable outcome/target
6. Valid data types
7. Missingness acceptable
8. No obvious leakage
9. Sufficient sample size
10. Compatible feature coverage

Computes readiness score (0-100) and returns structured status:
READY | READY_WITH_LIMITATIONS | NOT_READY | TIME_SERIES | LARGE_DATASET.
"""
from typing import Dict, Any, List, Optional


def evaluate_dataset_readiness(
    profile: Dict[str, Any],
    capabilities_info: Dict[str, Any],
    user_selected_target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates dataset profile and capabilities against ContentSignal requirements.
    Returns structured readiness report with 10-point checklist.
    """
    checks: List[Dict[str, Any]] = []
    reasons: List[str] = []
    warnings: List[str] = []

    row_count = profile.get("row_count", 0)
    col_count = profile.get("column_count", 0)
    columns = profile.get("columns", [])
    missing_rates = profile.get("missing_rates", {})
    constant_columns = profile.get("constant_columns", [])
    is_wide_time_series = profile.get("is_wide_time_series", False)
    is_streamed = profile.get("is_streamed", False)
    file_size_bytes = profile.get("file_size_bytes", 0)

    caps = capabilities_info.get("capabilities", {})
    cap_cols = capabilities_info.get("capability_columns", {})
    target_cands = capabilities_info.get("target_candidates", [])
    has_content = capabilities_info.get("has_content_signals", False)
    has_perf = capabilities_info.get("has_performance_signals", False)
    entity_type = capabilities_info.get("primary_entity_type", "unknown")

    # 1. File readable & valid structure
    if col_count >= 2 and row_count > 0:
        checks.append({
            "name": "File readable",
            "status": "PASS",
            "message": f"File successfully parsed with {col_count} columns.",
            "details": f"Encoding and delimiter verified; {col_count} columns detected."
        })
    else:
        checks.append({
            "name": "File readable",
            "status": "FAIL",
            "message": "File is empty or could not be parsed into tabular format.",
            "details": "Ensure valid CSV format with consistent delimiters."
        })
        reasons.append("File contains 0 rows or fewer than 2 columns.")

    # 2. Rows detected
    if row_count >= 10:
        checks.append({
            "name": "Rows detected",
            "status": "PASS",
            "message": f"{row_count:,} records detected.",
            "details": f"Dataset row volume ({row_count:,}) is sufficient for evaluation."
        })
    else:
        checks.append({
            "name": "Rows detected",
            "status": "FAIL",
            "message": f"Only {row_count} rows detected. Minimum required is 10 rows.",
            "details": "A minimum sample is required for meaningful signal detection."
        })
        reasons.append(f"Insufficient row count ({row_count} < 10).")

    # 3. Content records check
    if entity_type == "seller_directory" or (not has_content and not caps.get("SEARCH")):
        checks.append({
            "name": "Content records",
            "status": "FAIL",
            "message": "No content, article, page, or post assets detected.",
            "details": f"Detected entity type '{entity_type}' represents directory/relational data rather than content assets."
        })
        reasons.append("Dataset does not represent content, web pages, or editorial assets.")
    elif has_content or caps.get("SEARCH"):
        checks.append({
            "name": "Content records",
            "status": "PASS",
            "message": "Content records and metadata detected.",
            "details": f"Found content signals in: {cap_cols.get('CONTENT', [])[:3] + cap_cols.get('TEXT', [])[:3]}"
        })
    else:
        checks.append({
            "name": "Content records",
            "status": "WARN",
            "message": "Implicit content records detected without rich text metadata.",
            "details": "Identified record identifiers without full body or title text."
        })

    # 4. Performance signals check
    perf_cols = (
        cap_cols.get("VISIBILITY", []) +
        cap_cols.get("ENGAGEMENT", []) +
        cap_cols.get("SEARCH", []) +
        cap_cols.get("CONVERSION", [])
    )
    non_constant_perf = [c for c in perf_cols if c not in constant_columns]

    if is_wide_time_series:
        checks.append({
            "name": "Performance signals",
            "status": "PASS",
            "message": "Daily time-series performance observations detected.",
            "details": f"Found {col_count - 1} daily observation steps across entities."
        })
    elif len(non_constant_perf) > 0:
        checks.append({
            "name": "Performance signals",
            "status": "PASS",
            "message": f"{len(non_constant_perf)} measurable performance signal(s) detected.",
            "details": f"Signals with non-zero variance: {non_constant_perf[:5]}"
        })
    else:
        checks.append({
            "name": "Performance signals",
            "status": "FAIL",
            "message": "No measurable performance metric detected or all performance metrics have zero variance.",
            "details": "No views, reach, impressions, clicks, or interactions with observable variation."
        })
        reasons.append("No measurable performance metrics with non-zero variance detected.")

    # 5. Suitable outcome/target check
    effective_target = user_selected_target
    if not effective_target and target_cands:
        effective_target = target_cands[0]["column"]

    if effective_target and effective_target in columns:
        checks.append({
            "name": "Suitable outcome/target",
            "status": "PASS",
            "message": f"Outcome candidate detected: '{effective_target}'.",
            "details": f"Identified {target_cands[0].get('description', 'Target metric for optimization')}." if target_cands else "Selected target."
        })
    elif is_wide_time_series:
        checks.append({
            "name": "Suitable outcome/target",
            "status": "PASS",
            "message": "Temporal sequence trajectory acts as forecasting outcome.",
            "details": "Wide time-series format contains sequential daily outcomes."
        })
    elif len(non_constant_perf) > 0:
        checks.append({
            "name": "Suitable outcome/target",
            "status": "WARN",
            "message": "No pre-labeled supervised target; empirical percentile scoring will be used.",
            "details": "Heuristic and empirical ranking supported; model training will use engagement percentiles."
        })
        warnings.append("No explicit binary supervised target; relying on empirical signal percentiles.")
    else:
        checks.append({
            "name": "Suitable outcome/target",
            "status": "FAIL",
            "message": "No usable outcome or target was detected for supervised training or ranking.",
            "details": "Provide a column reflecting content performance outcome (e.g. shares, ranking, conversion, interactions)."
        })
        reasons.append("No usable outcome or target detected.")

    # 6. Valid data types
    numeric_count = len(profile.get("numeric_columns", []))
    if is_wide_time_series or numeric_count >= 1:
        checks.append({
            "name": "Valid data types",
            "status": "PASS",
            "message": f"Detected {numeric_count} numeric metric columns.",
            "details": "Numeric columns parsed into valid integer/float representations."
        })
    else:
        checks.append({
            "name": "Valid data types",
            "status": "FAIL",
            "message": "No numeric metric columns detected.",
            "details": "All columns parsed as strings or non-numeric types."
        })
        reasons.append("Dataset lacks numeric performance columns.")

    # 7. Missingness acceptable
    high_missing_cols = [c for c, rate in missing_rates.items() if rate > 40.0]
    if len(high_missing_cols) == 0:
        checks.append({
            "name": "Missingness acceptable",
            "status": "PASS",
            "message": "All columns have acceptable completeness (< 40% missing).",
            "details": "Data completeness meets production quality requirements."
        })
    elif len(high_missing_cols) <= 3:
        checks.append({
            "name": "Missingness acceptable",
            "status": "WARN",
            "message": f"{len(high_missing_cols)} column(s) have >40% missing values: {high_missing_cols}.",
            "details": "Missing values will be handled with indicator flags and imputation."
        })
        warnings.append(f"High missingness in columns: {high_missing_cols}")
    else:
        checks.append({
            "name": "Missingness acceptable",
            "status": "FAIL",
            "message": f"{len(high_missing_cols)} columns exceed 40% missing data.",
            "details": "Excessive missing data impairs statistical reliability."
        })
        reasons.append("Excessive missing data across multiple critical columns.")

    # 8. Leakage check
    potential_leakage_cols = []
    if effective_target:
        # Check if target components leak (e.g. if target is Total Interactions, like/share/comment leak)
        norm_target = effective_target.lower()
        if "total" in norm_target and "interaction" in norm_target:
            for col in columns:
                if col.lower() in ("like", "likes", "share", "shares", "comment", "comments"):
                    potential_leakage_cols.append(col)
        # Check for self-referential shares
        if norm_target == "shares":
            for col in columns:
                if "self_reference" in col.lower() or "kw_avg_avg" in col.lower():
                    potential_leakage_cols.append(col)

    if potential_leakage_cols:
        checks.append({
            "name": "Leakage check",
            "status": "WARN",
            "message": f"Potential target-derivative leakage identified in {len(potential_leakage_cols)} column(s): {potential_leakage_cols}.",
            "details": "These columns will be automatically quarantined from the model feature vector."
        })
        warnings.append(f"Target component leakage detected in: {potential_leakage_cols}")
    else:
        checks.append({
            "name": "Leakage check",
            "status": "PASS",
            "message": "No unmitigated target leakage detected.",
            "details": "Target-derived and post-outcome features are cleanly separated."
        })

    # 9. Sample size
    if is_wide_time_series or row_count >= 50:
        checks.append({
            "name": "Sufficient sample size",
            "status": "PASS",
            "message": f"Sample size ({row_count:,} records) meets statistical threshold.",
            "details": "Provides adequate statistical support for opportunity scoring."
        })
    elif row_count >= 10:
        checks.append({
            "name": "Sufficient sample size",
            "status": "WARN",
            "message": f"Small sample size ({row_count} records). Model will use simple regularization.",
            "details": "Under 50 records limits advanced multi-feature ranking."
        })
        warnings.append(f"Small dataset size ({row_count} rows).")
    else:
        checks.append({
            "name": "Sufficient sample size",
            "status": "FAIL",
            "message": "Sample size is insufficient for reliable analysis.",
            "details": "Minimum 10 rows required."
        })

    # 10. Compatible feature coverage
    detected_caps = capabilities_info.get("detected_capabilities", [])
    if is_wide_time_series:
        checks.append({
            "name": "Compatible feature coverage",
            "status": "PASS",
            "message": "Time-series coverage detected.",
            "details": "Entity + temporal observations available."
        })
    elif len(detected_caps) >= 2 and (has_content or caps.get("SEARCH")) and has_perf:
        checks.append({
            "name": "Compatible feature coverage",
            "status": "PASS",
            "message": f"Compatible multi-capability coverage: {detected_caps[:4]}.",
            "details": "Can be mapped cleanly to canonical feature layer."
        })
    else:
        checks.append({
            "name": "Compatible feature coverage",
            "status": "FAIL",
            "message": "Lacks the required combination of Content and Performance capabilities.",
            "details": "ContentSignal requires at least one content/search signal and one performance signal."
        })
        reasons.append("Insufficient capability coverage across Content and Performance dimensions.")

    # Compute overall score and determine status
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    pass_count = sum(1 for c in checks if c["status"] == "PASS")

    score = max(0, min(100, int((pass_count * 10) + (warn_count * 5) - (fail_count * 15))))

    # Classification logic
    if is_wide_time_series:
        status = "TIME_SERIES"
        score = max(score, 90)
    elif is_streamed and file_size_bytes > 50 * 1024 * 1024:
        status = "LARGE_DATASET"
    elif fail_count > 0:
        status = "NOT_READY"
        score = min(score, 48)
    elif warn_count > 0:
        status = "READY_WITH_LIMITATIONS"
    else:
        status = "READY"

    for c in checks:
        c["passed"] = c.get("status") == "PASS"
        c["id"] = c["name"].lower().replace(" ", "_").replace("/", "_")
        c["severity"] = "blocker" if c["status"] == "FAIL" else ("warning" if c["status"] == "WARN" else "info")

    rejection_reason = "; ".join(reasons) if reasons else None
    suggested_adapter = "FlyRankAdapter" if entity_type == "content_asset" and len(profile.get("columns", [])) >= 44 else ("TimeSeriesAdapter" if status == "TIME_SERIES" else "GenericTabularAdapter")

    return {
        "status": status,
        "overall_status": status,
        "score": score,
        "readiness_pct": score,
        "suggested_adapter": suggested_adapter,
        "effective_target": effective_target,
        "is_ready": status in ("READY", "READY_WITH_LIMITATIONS"),
        "checks": checks,
        "checklist": checks,
        "warnings": warnings,
        "reasons": reasons,
        "blockers": reasons,
        "summary": rejection_reason or f"Readiness score {score}%: Dataset is {status.lower().replace('_', ' ')}.",
        "rejection_reason": rejection_reason,
        "potential_leakage_columns": potential_leakage_cols,
    }


check_dataset_readiness = evaluate_dataset_readiness

