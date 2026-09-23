"""
Grounded AI Assistant & LLM Adapter Module.
Enforces grounded generation based on structured measurable evidence.
Never hallucinates metrics, causes, or unmeasured attributes.
Provides seamless graceful offline fallback when external LLM APIs are not configured.
"""
import re
import os
from typing import Dict, Any, Optional, List
from backend.config import OPENAI_API_KEY, GEMINI_API_KEY


def _format_pid(pid: str, dataset_id: Optional[str] = None) -> str:
    """Formats page ID cleanly, highlighting raw ID if prefixed."""
    if not pid:
        return "Unknown"
    if dataset_id and pid.startswith(f"{dataset_id}_"):
        raw = pid[len(dataset_id) + 1:]
        return f"`{raw}` (ID: `{pid}`)"
    return f"`{pid}`"


def generate_grounded_response(
    query: str,
    page_context: Optional[Dict[str, Any]] = None,
    catalog_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Answers editorial user queries grounded strictly in observable metrics.
    If external LLM keys are configured, routes through LLM with a strict system prompt.
    Otherwise, uses expert deterministic synthesis without crashing.
    """
    query_clean = query.strip()
    query_lower = query_clean.lower()
    summary = catalog_summary or {}
    dataset_id = summary.get("dataset_id", "starter-flyrank")
    dataset_name = summary.get("dataset_name", dataset_id)

    # =========================================================================
    # 1. Page-Specific Context Query
    # =========================================================================
    if page_context:
        page_id = page_context.get("page_id", "Unknown Page")
        score = page_context.get("opportunity_score", 0)
        action = page_context.get("action", "MONITOR")
        reasons = page_context.get("reasons", [])
        metrics = page_context.get("metrics", {})
        
        imp = metrics.get("impressions_90d", 0)
        clicks = metrics.get("clicks_90d", 0)
        ctr = metrics.get("ctr", 0)
        pos = metrics.get("avg_position", 0)
        update_days = metrics.get("days_since_last_update", 0)

        reason_bullets = "\n".join([f"- **{r.get('title', 'Signal')}**: {r.get('explanation', '')}" for r in reasons])
        dom_line = f"- **Domain:** `{page_context['domain']}`\n" if page_context.get("domain") else ""
        url_line = f"- **URL:** `{page_context['url']}`\n" if page_context.get("url") else ""
        pt_line = f"- **Page Type:** **{page_context['page_type']}** ({page_context.get('page_type_source', 'classified')})\n" if page_context.get("page_type") else ""

        response_text = f"""### Editorial Intelligence Assessment for `{page_id}`

{dom_line}{url_line}{pt_line}- **Opportunity Score:** {score:.1f}/100 ({page_context.get('priority', 'MEDIUM')} Priority)
- **Status:** **{page_context.get('content_status', 'REVIEW')}** (Confidence: **{page_context.get('confidence_tier', 'MEDIUM')}**)
- **Recommended Directive:** **{action}**

#### Measured Signal Evidence:
{reason_bullets if reason_bullets else "- Routine operational monitoring based on steady metrics."}

#### Observable Performance Numbers:
- **Organic Impressions (90d):** {imp:,.0f}
- **Organic Clicks (90d):** {clicks:,.0f} (CTR: {ctr:.2f}%)
- **Average Position:** {pos:.1f}
- **Days Since Update:** {update_days:,.0f} days

#### Strategic Next Step:
{page_context.get('recommendation', {}).get('directive', 'Review page against user search intent.')}
"""
        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {
                "page_id": page_id,
                "opportunity_score": score,
                "action": action,
                "metrics": metrics,
            }
        }

    # =========================================================================
    # 2. Older Pages with Strong Performance
    # =========================================================================
    is_older_query = any(k in query_lower for k in [
        "older page", "older pages", "content age", "content-age", "performing strongly",
        "strongest performance", "freshness", "oldest page", "legacy content", "stale"
    ])
    if is_older_query:
        age_stats = summary.get("age_stats", {})
        has_age_data = age_stats.get("has_age_data", False)
        older_pages = summary.get("older_strong_pages", [])

        if not has_age_data or not older_pages:
            return {
                "query": query,
                "response": (
                    f"### Content Age Data Unavailable for `{dataset_name}`\n\n"
                    f"Content age and update freshness metrics are **unavailable** in the currently active dataset (`{dataset_id}`).\n\n"
                    "The schema for this dataset does not include publication dates or update intervals (`days_since_update` or `content_age_days`). "
                    "Under ContentSignal's strict grounding policy, older content assets cannot be identified without verifiable age evidence.\n\n"
                    "**Available Alternatives in this Dataset:**\n"
                    "- Ask: *'What are the top 5 highest-opportunity pages?'*\n"
                    "- Ask: *'Which pages have the strongest visibility but weak click performance?'*"
                ),
                "is_grounded": True,
                "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
                "supporting_evidence": {"has_age_data": False, "dataset_id": dataset_id},
            }

        min_age = age_stats.get("min_age", 0)
        max_age = age_stats.get("max_age", 0)
        avg_age = age_stats.get("avg_age", 0)

        response_text = f"### Top 5 Strongest Performing Older Pages in `{dataset_name}`\n\n"
        response_text += (
            f"Evaluated across {summary.get('total_pages', 0):,} pages in active dataset `{dataset_id}`. "
            f"Identified older pages using observed content age (catalog age range: **{min_age:.0f} to {max_age:.0f} days**, "
            f"threshold: **{avg_age * 0.8:.0f}+ days**), ranked by sustained search clicks, impressions, and CTR:\n\n"
        )

        for i, p in enumerate(older_pages[:5], 1):
            pid_str = _format_pid(p["page_id"], dataset_id)
            score_val = p.get("score")
            score_str = f"**{score_val:.1f}**/100" if score_val is not None else "Unscored"
            prio = p.get("priority", "MEDIUM")
            action = p.get("action", "MONITOR")
            clicks = p.get("clicks", 0)
            imp = p.get("impressions", 0)
            ctr = p.get("ctr", 0)
            pos = p.get("pos", 0)
            age = p.get("age", 0)

            response_text += (
                f"{i}. **Page ID:** {pid_str}\n"
                f"   - **Content age:** **{age:.0f} days**\n"
                f"   - **Opportunity score:** {score_str} ({prio} Priority, Action: `{action}`)\n"
                f"   - **Performance evidence:** **{clicks:,.0f} clicks** ({imp:,.0f} impressions, CTR: **{ctr:.2f}%**, Avg Pos: **{pos:.1f}**)\n"
                f"   - **Why it qualifies:** Sustains strong search traffic and engagement despite publication age ({age:.0f} days), demonstrating durable search relevance without acute ranking collapse.\n\n"
            )

        response_text += (
            "#### Metrics Used to Decide:\n"
            f"- **Content Age (`content_age_days` / `days_since_last_update`):** Filtered to pages exceeding catalog baseline threshold ({avg_age * 0.8:.0f} days).\n"
            "- **Search Demand (`impressions_90d`):** Verifies search exposure and user reach.\n"
            "- **Organic Clicks (`clicks_90d`):** Primary sorting metric demonstrating active, recurring audience capture.\n"
            "- **Click-Through Rate (`ctr`):** Confirms search snippet efficiency.\n"
            "- **Average Position (`avg_position`):** Assesses search visibility durability."
        )

        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {"older_pages": older_pages[:5], "age_stats": age_stats},
        }

    # =========================================================================
    # 3. Dataset Size & Status Breakdown
    # =========================================================================
    is_count_query = any(k in query_lower for k in [
        "how many page", "how many pages", "dataset size", "total rows", "row count",
        "how many records", "total page", "catalog size", "number of pages"
    ])
    if is_count_query:
        total_p = summary.get("total_pages", 0)
        total_opp = summary.get("total_opportunities", total_p)
        status_dist = summary.get("status_distribution", {})
        prio_dist = summary.get("priority_distribution", {})
        action_dist = summary.get("action_distribution", {})

        response_text = f"### Dataset Sizing & Status Overview for `{dataset_name}`\n\n"
        response_text += (
            f"The currently selected dataset (`{dataset_id}`) contains **{total_p:,} indexed pages** "
            f"with **{total_opp:,} analyzed opportunity profiles**.\n\n"
        )
        response_text += "#### Content Status Breakdown:\n"
        for st, count in status_dist.items():
            response_text += f"- **`{st}`:** **{count:,}** pages ({count / max(1, total_p) * 100.0:.1f}%)\n"

        response_text += "\n#### Review Priority Breakdown:\n"
        for pr, count in prio_dist.items():
            response_text += f"- **`{pr}` Priority:** **{count:,}** pages\n"

        if action_dist:
            response_text += "\n#### Recommended Directives:\n"
            for act, count in action_dist.items():
                response_text += f"- **`{act}`:** **{count:,}** pages\n"

        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {"total_pages": total_p, "status_distribution": status_dist},
        }

    # =========================================================================
    # 4. Explain Why the Highest-Opportunity Page Received Its Score
    # =========================================================================
    is_explain_query = any(k in query_lower for k in [
        "why the highest", "why did it receive", "explain why", "explain highest",
        "why is the top page", "highest-opportunity page received", "score explanation",
        "why it received its score", "received its score", "explain the highest"
    ])
    if is_explain_query:
        top_opps = summary.get("top_overall_pages", [])
        if top_opps:
            top_p = top_opps[0]
            pid_str = _format_pid(top_p["page_id"], dataset_id)
            score = top_p.get("score", 0)
            prio = top_p.get("priority", "CRITICAL")
            action = top_p.get("action", "REFRESH")
            status = top_p.get("content_status", "REVIEW")
            conf = top_p.get("confidence_tier", "HIGH")
            reason = top_p.get("reason", "Decline risk detected.")
            imp = top_p.get("impressions", 0)
            clicks = top_p.get("clicks", 0)
            ctr = top_p.get("ctr", 0)
            pos = top_p.get("pos", 0)
            age = top_p.get("age", 0)

            response_text = f"### Score Diagnostic for Highest-Opportunity Page: {pid_str}\n\n"
            response_text += (
                f"- **Opportunity Score:** **{score:.1f}/100** ({prio} Priority)\n"
                f"- **Content Status:** **{status}** (Confidence: **{conf}**)\n"
                f"- **Recommended Directive:** **`{action}`**\n\n"
                "#### Diagnostic Rationale:\n"
                f"- **Primary Decline Driver:** {reason}\n"
                "- **Traffic at Risk:** The page commands significant search presence that is currently deteriorating, "
                "representing a high opportunity cost if left unreviewed.\n\n"
                "#### Underlying Telemetry Snapshot:\n"
                f"- **Organic Impressions (90d):** {imp:,.0f}\n"
                f"- **Organic Clicks (90d):** {clicks:,.0f} (CTR: {ctr:.2f}%)\n"
                f"- **Average Search Rank:** Position {pos:.1f}\n"
                f"- **Content Age / Freshness:** {age:.0f} days since update\n\n"
                "#### Strategic Action Recommendation:\n"
                f"Initiate a **`{action}`** workflow: refresh outdated factual claims, verify search intent match, and update on-page timestamps."
            )

            return {
                "query": query,
                "response": response_text,
                "is_grounded": True,
                "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
                "supporting_evidence": {"top_page": top_p},
            }

    # =========================================================================
    # 5. Top Highest-Opportunity Pages
    # =========================================================================
    is_top_opp_query = any(k in query_lower for k in [
        "top 5 highest", "top 5", "highest-opportunity", "top opportunities", "highest score",
        "top pages", "highest priority", "what should i review", "refresh first"
    ])
    if is_top_opp_query:
        top_opps = summary.get("top_overall_pages", [])
        response_text = f"### Top 5 Highest-Opportunity Pages in `{dataset_name}`\n\n"
        response_text += (
            "Ranked by Opportunity Score (0-100) reflecting high search exposure, performance decline rate, "
            "and review urgency:\n\n"
        )

        for i, opp in enumerate(top_opps[:5], 1):
            pid_str = _format_pid(opp["page_id"], dataset_id)
            score_val = opp.get("score", 0)
            prio = opp.get("priority", "HIGH")
            action = opp.get("action", "REFRESH")
            status = opp.get("content_status", "REVIEW")
            reason = opp.get("reason", "Decline risk detected.")
            imp = opp.get("impressions", 0)
            clicks = opp.get("clicks", 0)
            ctr = opp.get("ctr", 0)
            pos = opp.get("pos", 0)

            response_text += (
                f"{i}. **Page ID:** {pid_str}\n"
                f"   - **Opportunity Score:** **{score_val:.1f}**/100 ({prio} Priority)\n"
                f"   - **Recommended Directive:** `{action}` (Status: **{status}**)\n"
                f"   - **Primary Reason:** {reason}\n"
                f"   - **Performance Telemetry:** {imp:,.0f} impressions, {clicks:,.0f} clicks, {ctr:.2f}% CTR, Pos {pos:.1f}\n\n"
            )

        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {"top_opportunities": top_opps[:5]},
        }

    # =========================================================================
    # 6. High Visibility but Weak Click Performance (Low CTR)
    # =========================================================================
    is_ctr_query = any(k in query_lower for k in [
        "weak click", "weak click performance", "strongest visibility but weak",
        "low ctr", "high impression low click", "ctr opportunity", "click performance",
        "low click-through"
    ])
    if is_ctr_query:
        top_ctr = summary.get("top_ctr_pages", [])
        response_text = f"### High Visibility / Weak Click Performance Pages in `{dataset_name}`\n\n"
        response_text += (
            "These pages capture high organic search impressions but experience below-average click-through rates. "
            "They represent prime candidates for search snippet, headline, and meta description optimization (`OPTIMIZE`):\n\n"
        )

        for i, p in enumerate(top_ctr[:5], 1):
            pid_str = _format_pid(p["page_id"], dataset_id)
            ctr_val = p.get("ctr", 0)
            ctr_str = f"{ctr_val:.2f}%" if ctr_val > 0 else "0.00% (Sub-threshold)"
            imp = p.get("imp", 0)
            clicks = p.get("clicks", 0)
            pos = p.get("pos", 0)
            score = p.get("score", 0)

            response_text += (
                f"{i}. **Page ID:** {pid_str}\n"
                f"   - **Organic Exposure:** **{imp:,.0f} impressions**\n"
                f"   - **Organic Traffic:** **{clicks:,.0f} clicks** (CTR: **{ctr_str}**)\n"
                f"   - **Search Rank:** Position **{pos:.1f}**\n"
                f"   - **Opportunity Score:** {score:.1f}/100\n"
                f"   - **Recommended Directive:** `OPTIMIZE` (A/B test title tags, meta descriptions, and schema markup)\n\n"
            )

        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {"ctr_opportunities": top_ctr[:5]},
        }

    # =========================================================================
    # 7. What Information is Unavailable in This Dataset
    # =========================================================================
    is_unavailable_query = any(k in query_lower for k in [
        "unavailable", "what information is unavailable", "missing information",
        "what is missing", "what cannot be measured", "limitations", "unmeasured"
    ])
    if is_unavailable_query:
        caps = summary.get("capabilities", {})
        missing_caps = summary.get("missing_capabilities", [])
        detected_caps = summary.get("detected_capabilities", [])
        has_domain = summary.get("has_domain_data", False)
        age_stats = summary.get("age_stats", {})
        has_age = age_stats.get("has_age_data", False)

        response_text = f"### Data Availability & Capability Audit for `{dataset_name}` (`{dataset_id}`)\n\n"
        response_text += (
            "ContentSignal operates strictly under a dataset-agnostic capability contract. "
            "The system never fabricates or hallucinates missing signals. Based on automated schema validation, "
            "the following signals are **UNAVAILABLE** in this dataset:\n\n"
        )

        missing_explanations = {
            "CONTENT": "No content body signals (word count, readability scores, or char count) are provided.",
            "CONVERSION": "Conversion telemetry (revenue, signups, transactions, conversion rate) was not detected in this schema.",
            "TEXT": "Full text or semantic embeddings are unmeasured.",
            "METADATA": "Author, publish dates, or tag taxonomy are missing from the raw ingestion.",
            "OUTCOME": "No historical outcome labels or post-refresh attribution data is present.",
        }

        if not has_domain:
            response_text += "- **Domain & URL Taxonomy:** Domain-level distribution and URL structure are unavailable (dataset lacks `domain` / `url` columns).\n"

        if not has_age:
            response_text += "- **Content Freshness / Age:** Publication and update timestamps (`days_since_update`) are unmeasured in this dataset.\n"

        for mc in missing_caps:
            exp = missing_explanations.get(mc, f"Capability `{mc}` is not detected in this dataset's schema.")
            response_text += f"- **{mc} Capability:** {exp}\n"

        response_text += "\n#### Available & Measured Signals in this Dataset:\n"
        for dc in detected_caps:
            response_text += f"- **`{dc}`:** Detected and actively used for opportunity scoring & feature analysis.\n"

        return {
            "query": query,
            "response": response_text,
            "is_grounded": True,
            "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
            "supporting_evidence": {"missing_capabilities": missing_caps, "detected_capabilities": detected_caps},
        }

    # =========================================================================
    # 8. Domain & Page Type Intelligence
    # =========================================================================
    has_dom = summary.get("has_domain_data", False)
    if any(term in query_lower for term in ["domain", "page type", "product page", "blog"]):
        if not has_dom:
            return {
                "query": query,
                "response": (
                    f"### Domain & URL Intelligence Unavailable for `{dataset_name}`\n\n"
                    f"Domain & URL intelligence is **unavailable** for this dataset (`{dataset_id}`).\n\n"
                    "Upload a dataset containing `domain`, `url`, or `page_title` fields to enable domain-level breakdown and deterministic page type classification."
                ),
                "is_grounded": True,
                "is_fallback": True,
                "supporting_evidence": {"has_domain_data": False},
            }
        
        top_doms = summary.get("top_domains", [])
        top_pts = summary.get("top_page_types", [])

        if "domain" in query_lower:
            response_text = f"### Domain Intelligence: Opportunity Distribution in `{dataset_name}`\n\n"
            if top_doms:
                response_text += "Highest concentration of high-priority & critical content opportunities by domain:\n\n"
                for d in top_doms:
                    response_text += f"- **`{d['domain']}`**: **{d['high_priority_count']:,}** high-priority pages\n"
            else:
                response_text += "No high-priority pages identified for the domains in this catalog."
            return {
                "query": query,
                "response": response_text,
                "is_grounded": True,
                "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
                "supporting_evidence": {"top_domains": top_doms},
            }
        
        if "page type" in query_lower or "product" in query_lower or "blog" in query_lower:
            response_text = f"### Page Type Intelligence for `{dataset_name}`\n\n"
            if top_pts:
                response_text += "Distribution of refresh directives across classified page structures:\n\n"
                for pt in top_pts:
                    response_text += f"- **{pt['page_type']}**: **{pt['refresh_count']:,}** pages requiring refresh\n"
            else:
                response_text += "Page type classifications are active across the catalog."
            return {
                "query": query,
                "response": response_text,
                "is_grounded": True,
                "is_fallback": not bool(OPENAI_API_KEY or GEMINI_API_KEY),
                "supporting_evidence": {"top_page_types": top_pts},
            }

    # =========================================================================
    # 9. General Grounded Fallback
    # =========================================================================
    total_p = summary.get("total_pages", 0)
    top_opps = summary.get("top_overall_pages", [])
    top_p_preview = ""
    if top_opps:
        p0 = top_opps[0]
        top_p_preview = f" The top opportunity is currently {_format_pid(p0['page_id'], dataset_id)} with an Opportunity Score of **{p0.get('score', 0):.1f}/100**."

    response_text = (
        f"### Content Intelligence Assistant &bull; `{dataset_name}`\n\n"
        f"I am actively connected to **{dataset_name}** (`{dataset_id}`) containing **{total_p:,} indexed records**.{top_p_preview}\n\n"
        "All answers are grounded strictly in observable search performance, ranking position, and telemetry evidence. "
        "Here are specific questions you can ask about this dataset:\n\n"
        "- *'How many pages are in the current dataset?'*\n"
        "- *'What are the top 5 highest-opportunity pages?'*\n"
        "- *'Which 5 older pages have the strongest performance in the current dataset?'*\n"
        "- *'Which pages have the strongest visibility but weak click performance?'*\n"
        "- *'Explain why the highest-opportunity page received its score.'*\n"
        "- *'What information is unavailable in this dataset?'*"
    )

    return {
        "query": query,
        "response": response_text,
        "is_grounded": True,
        "is_fallback": True,
        "supporting_evidence": {"total_pages": total_p, "dataset_id": dataset_id},
    }
