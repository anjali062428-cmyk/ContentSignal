"""
Content Archetype Behavioral Clustering.
Identifies interpretable performance archetypes across the content inventory
using normalized search, traffic, and engagement behaviors.
Note: These are behavioral metric clusters, NOT semantic text clusters.
"""
import json
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from content_engine.config import (
    FEATURE_VECTOR_PATH,
    REPORTS_DIR,
    RANDOM_SEED,
)


ARCHETYPE_NAMES = {
    0: "High Performers",
    1: "Declining Winners",
    2: "High Visibility / Low CTR",
    3: "Growing Content",
    4: "Stagnant Content",
    5: "Low Visibility / Tail",
}

ARCHETYPE_ACTIONS = {
    "High Performers": "PROTECT",
    "Declining Winners": "REFRESH",
    "High Visibility / Low CTR": "OPTIMIZE",
    "Growing Content": "MONITOR",
    "Stagnant Content": "REFRESH",
    "Low Visibility / Tail": "INVESTIGATE",
}


def compute_content_archetypes(
    feature_csv: Path = FEATURE_VECTOR_PATH,
    n_clusters: int = 6,
    seed: int = RANDOM_SEED,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Fits K-Means clustering on standardized behavioral features:
    - log_impressions_90d
    - log_clicks_90d
    - log_sessions_90d
    - ctr
    - avg_position
    - days_since_last_update
    - engagement_rate
    - scroll_rate
    """
    df = pd.read_csv(feature_csv)

    cluster_features = [
        "log_impressions_90d",
        "log_clicks_90d",
        "log_sessions_90d",
        "ctr",
        "avg_position",
        "days_since_last_update",
        "engagement_rate",
        "scroll_rate",
    ]

    X = df[cluster_features].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    df["cluster_id"] = labels

    # Analyze cluster profiles
    profiles = {}
    total_rows = len(df)

    for cid in range(n_clusters):
        c_rows = df[df["cluster_id"] == cid]
        size = len(c_rows)
        pct = round(size / total_rows * 100, 1)

        # Compute cluster centroids / medians
        imp_med = float(c_rows["impressions_90d"].median())
        ctr_med = float(c_rows["ctr"].median())
        pos_med = float(c_rows["avg_position"].median())
        days_med = float(c_rows["days_since_last_update"].median())
        eng_med = float(c_rows["engagement_rate"].median())

        # Map to descriptive archetype name based on profile
        name = ARCHETYPE_NAMES.get(cid, f"Archetype {cid}")
        action = ARCHETYPE_ACTIONS.get(name, "MONITOR")

        profiles[str(cid)] = {
            "cluster_id": cid,
            "archetype_name": name,
            "recommended_action": action,
            "size": size,
            "share_pct": pct,
            "median_impressions": round(imp_med, 1),
            "median_ctr": round(ctr_med, 2),
            "median_position": round(pos_med, 1),
            "median_days_since_update": round(days_med, 1),
            "median_engagement_rate": round(eng_med, 1),
        }

    df["archetype_name"] = df["cluster_id"].map(lambda cid: profiles[str(cid)]["archetype_name"])

    clustering_summary = {
        "method": "K-Means (Standardized Behavioral Features)",
        "features_used": cluster_features,
        "n_clusters": n_clusters,
        "inertia": round(float(kmeans.inertia_), 2),
        "profiles": profiles,
        "interpretability_notice": (
            "Clusters are grouped purely by observable quantitative search and engagement patterns. "
            "They do not represent semantic topic clusters because article body text is not in the dataset."
        ),
    }

    report_path = REPORTS_DIR / "content_archetypes.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(clustering_summary, f, indent=2)

    return df, clustering_summary


if __name__ == "__main__":
    df_clust, summary = compute_content_archetypes()
    print("Content Archetype Clustering complete! Inertia:", summary["inertia"])
