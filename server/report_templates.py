"""
Report templates + render helpers.

This module intentionally keeps templates "data-ready" (no example values),
and fills them with whatever TimelineAnalysis already contains (no new context).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple


SECURITY_INCIDENT_REPORT_TEMPLATE_MD = """# Security Incident Report

**Incident ID:** {incident_id}

**Severity:** {severity}

**Status:** {status}

**Prepared By:** {prepared_by}

**Team:** {team}

**Date:** {date}

**Reviewed By:** {reviewed_by}

---

## 1. Executive Summary

{executive_summary}

---

## 2. The 5Ws (Core Analysis)

### **Who**

- Account: {who_account}
- Privilege Level: {who_privilege_level}
- Authentication: {who_authentication}

### **What**

- Observed Activity: {what_observed_activity}
- Key Evidence: {what_key_evidence}

### **When**

- Start Time: {when_start_time}
- End Time: {when_end_time}

### **Where**

- Device / Host: {where_host}
- Source IP / Geo: {where_source_ip_geo}
- Destination: {where_destination}

### **Why (Final Verdict)**

- Verdict: {why_verdict}
- Reasoning:
    
    {why_reasoning}

---

## 3. Impact Assessment

- Systems Impacted: {impact_systems}
- Data Exposure: {impact_data_exposure}
- Business Impact: {impact_business}

---

## 4. Actions Taken

{actions_taken}

---

## 5. Root Cause (If Applicable)

{root_cause}

---

## 6. Recommendations

{recommendations}

---

## 7. Audit & Compliance Notes

- Log Sources Reviewed: {audit_log_sources}
- Evidence Retention: {audit_evidence_retention}
- Control Mapping:
    - {audit_control_1}
    - {audit_control_2}

---

**Closure Date:** {closure_date}

**Confidence Level:** {confidence_level}

---
"""


def _dash_if_empty(val: Optional[str]) -> str:
    s = (val or "").strip()
    return s if s else "—"


def _fmt_dt_iso(dt: Any) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        # Keep it compact but readable
        return dt.isoformat(sep=" ", timespec="seconds")
    try:
        return str(dt)
    except Exception:
        return "—"


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(v)
    except Exception:
        return ""


def _extract_common_values(items: List[str], max_items: int = 3) -> List[str]:
    """
    Return most common values preserving order by frequency.
    """
    freq: Dict[str, int] = {}
    for it in items:
        key = (it or "").strip()
        if not key:
            continue
        freq[key] = freq.get(key, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [k for k, _ in ranked[:max_items]]


def _extract_actors_processes(analysis_payload: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    actors: List[str] = []
    procs: List[str] = []

    sequences = analysis_payload.get("suspicious_sequences") or []
    if isinstance(sequences, list):
        for seq in sequences:
            if not isinstance(seq, dict):
                continue
            events = seq.get("events_involved") or []
            if not isinstance(events, list):
                continue
            for ev in events:
                if not isinstance(ev, dict):
                    continue
                actor = _safe_str(ev.get("actor")).strip()
                proc = _safe_str(ev.get("process")).strip()
                if actor and actor.lower() not in {"n/a", "na", "unknown", "none"}:
                    actors.append(actor)
                if proc and proc.lower() not in {"n/a", "na", "unknown", "none"}:
                    procs.append(proc)

    events = analysis_payload.get("suspicious_events") or []
    if isinstance(events, list):
        for e in events:
            if not isinstance(e, dict):
                continue
            ev = e.get("event") or {}
            if not isinstance(ev, dict):
                continue
            actor = _safe_str(ev.get("actor")).strip()
            proc = _safe_str(ev.get("process")).strip()
            if actor and actor.lower() not in {"n/a", "na", "unknown", "none"}:
                actors.append(actor)
            if proc and proc.lower() not in {"n/a", "na", "unknown", "none"}:
                procs.append(proc)

    return _extract_common_values(actors), _extract_common_values(procs)


def _extract_key_evidence(analysis_payload: Dict[str, Any]) -> str:
    """
    Build a concise evidence summary from suspicious sequences/events without adding new context.
    """
    bullets: List[str] = []

    sequences = analysis_payload.get("suspicious_sequences") or []
    if isinstance(sequences, list) and sequences:
        # Prefer first sequence (already ordered by the AI in practice)
        seq0 = sequences[0] if isinstance(sequences[0], dict) else None
        if isinstance(seq0, dict):
            sid = _dash_if_empty(_safe_str(seq0.get("sequence_id")))
            sev = _dash_if_empty(_safe_str(seq0.get("severity")))
            conf = _dash_if_empty(_safe_str(seq0.get("confidence")))
            bullets.append(f"Sequence {sid} (Severity: {sev}, Confidence: {conf}%)")

            involved = seq0.get("events_involved") or []
            paths: List[str] = []
            if isinstance(involved, list):
                for ev in involved:
                    if isinstance(ev, dict):
                        p = _safe_str(ev.get("path")).strip()
                        if p and p.lower() not in {"n/a", "na"}:
                            paths.append(p)
            uniq_paths = []
            for p in paths:
                if p not in uniq_paths:
                    uniq_paths.append(p)
            if uniq_paths:
                sample = ", ".join(f"`{p}`" for p in uniq_paths[:3])
                bullets.append(f"Evidence paths: {sample}")

    events = analysis_payload.get("suspicious_events") or []
    if isinstance(events, list) and events:
        e0 = events[0] if isinstance(events[0], dict) else None
        if isinstance(e0, dict):
            eid = _dash_if_empty(_safe_str(e0.get("event_id")))
            sev = _dash_if_empty(_safe_str(e0.get("severity")))
            conf = _dash_if_empty(_safe_str(e0.get("confidence")))
            action = ""
            ev = e0.get("event") or {}
            if isinstance(ev, dict):
                action = _safe_str(ev.get("action")).strip()
            action = action or "Suspicious event"
            bullets.append(f"Event {eid}: {action} (Severity: {sev}, Confidence: {conf}%)")

    if not bullets:
        return "—"
    return "\n".join(f"- {b}" for b in bullets)


def _detect_privilege_level(text_blob: str) -> str:
    t = (text_blob or "").lower()
    if "administrator privileges" in t or "admin privileges" in t or "admin user" in t or "with administrator" in t:
        return "Admin"
    return "—"


def render_security_incident_report_markdown(
    *,
    analysis_dict: Dict[str, Any],
    prepared_by: Optional[str] = None,
    status: Optional[str] = None,
) -> str:
    """
    Render a Security Incident Report markdown using existing analysis data only.

    analysis_dict is expected to be TimelineAnalysis.as_dict().
    """
    analysis_payload = analysis_dict.get("analysis") or {}
    summary = (analysis_payload.get("summary") or {}) if isinstance(analysis_payload, dict) else {}

    # Executive summary: prefer verbose_summary, fall back to key_findings
    verbose_summary = ""
    if isinstance(analysis_payload, dict):
        verbose_summary = (analysis_payload.get("verbose_summary") or "") if isinstance(analysis_payload.get("verbose_summary"), str) else ""
        if not verbose_summary and isinstance(analysis_payload.get("human_readable_summary"), str):
            verbose_summary = analysis_payload.get("human_readable_summary") or ""
    if not verbose_summary:
        kf = summary.get("key_findings")
        if isinstance(kf, list) and kf:
            verbose_summary = "\n".join(f"- {str(x)}" for x in kf if x is not None).strip()
    executive_summary = _dash_if_empty(verbose_summary)

    # Recommendations: remediation_steps list when present
    recs = summary.get("remediation_steps")
    recommendations = "—"
    if isinstance(recs, list) and recs:
        recommendations = "\n".join(f"- {str(x)}" for x in recs if x is not None).strip() or "—"

    # Fields we can derive without inventing new context
    incident_id = _dash_if_empty(str(analysis_dict.get("id")) if analysis_dict.get("id") is not None else "")
    severity = _dash_if_empty(str(analysis_dict.get("overall_risk") or ""))
    confidence_level = _dash_if_empty(f"{analysis_dict.get('confidence')}%" if analysis_dict.get("confidence") is not None else "")

    # Status can be passed in (UI may want Closed/Monitoring), otherwise use DB status string
    report_status = status if status is not None else analysis_dict.get("status")
    report_status = _dash_if_empty(str(report_status or ""))

    # Device / host, source IP
    where_host = _dash_if_empty(str(analysis_dict.get("client_hostname") or ""))
    where_ip = analysis_dict.get("client_ip") or analysis_dict.get("ip_address") or ""
    where_source_ip_geo = _dash_if_empty(str(where_ip))

    # Time range
    when_start_time = _fmt_dt_iso(analysis_dict.get("start_time"))
    when_end_time = _fmt_dt_iso(analysis_dict.get("end_time"))

    # What: attack type is the safest existing label
    what_observed_activity = _dash_if_empty(str(analysis_dict.get("attack_type") or summary.get("attack_type") or ""))

    # Who: best-effort from analysis sequences/events
    actors, procs = ([], [])
    if isinstance(analysis_payload, dict):
        actors, procs = _extract_actors_processes(analysis_payload)
    who_account = _dash_if_empty(", ".join(actors) if actors else "")

    # Privilege level: detect from AI text only (no assumptions)
    who_priv = _detect_privilege_level(executive_summary)

    # Key evidence: from suspicious sequences/events
    what_key_evidence = "—"
    if isinstance(analysis_payload, dict):
        what_key_evidence = _extract_key_evidence(analysis_payload)

    # Why verdict: derive from overall risk + whether suspicious items exist
    suspicious_count = 0
    if isinstance(analysis_payload, dict):
        ss = analysis_payload.get("suspicious_sequences")
        se = analysis_payload.get("suspicious_events")
        suspicious_count = (len(ss) if isinstance(ss, list) else 0) + (len(se) if isinstance(se, list) else 0)
    why_verdict = "—"
    if severity != "—":
        why_verdict = f"{severity} risk — " + ("suspicious activity observed" if suspicious_count > 0 else "no suspicious activity observed")

    why_reasoning = _dash_if_empty(executive_summary if executive_summary != "—" else "")

    # Impact: use host and AI's own description (no new claims)
    impact_systems = _dash_if_empty(where_host if where_host != "—" else "")
    impact_business = severity if severity != "—" else "—"
    impact_data_exposure = "—"
    if isinstance(executive_summary, str) and executive_summary != "—":
        lower = executive_summary.lower()
        if "no overt signs" in lower or "no evidence" in lower or "no signs" in lower:
            impact_data_exposure = "No evidence observed in the provided telemetry"

    # Date
    date_val = analysis_dict.get("created_at")
    date_str = _dash_if_empty(str(date_val).split("T")[0] if isinstance(date_val, str) and "T" in date_val else str(date_val or ""))

    # Audit sources: based on counts (no extra detail)
    sources: List[str] = []
    fim_count = analysis_dict.get("fim_events_count")
    wazuh_count = analysis_dict.get("wazuh_events_count")
    if fim_count is not None:
        sources.append("FIM")
    if wazuh_count and int(wazuh_count) > 0:
        sources.append("SIEM")
    audit_sources = _dash_if_empty(", ".join(sources) if sources else "")

    # Fill template, leaving everything else as "—" (data-ready but readable)
    md = SECURITY_INCIDENT_REPORT_TEMPLATE_MD.format(
        incident_id=incident_id,
        severity=severity,
        status=report_status,
        prepared_by=_dash_if_empty(prepared_by),
        team="—",
        date=_dash_if_empty(date_str),
        reviewed_by="—",
        executive_summary=executive_summary,
        who_account=who_account,
        who_privilege_level=who_priv,
        who_authentication="—",
        what_observed_activity=what_observed_activity,
        what_key_evidence=what_key_evidence,
        when_start_time=when_start_time,
        when_end_time=when_end_time,
        where_host=where_host,
        where_source_ip_geo=where_source_ip_geo,
        where_destination="—",
        why_verdict=why_verdict,
        why_reasoning=why_reasoning,
        impact_systems=impact_systems,
        impact_data_exposure=impact_data_exposure,
        impact_business=impact_business,
        actions_taken="—",
        root_cause="—",
        recommendations=recommendations,
        audit_log_sources=audit_sources,
        audit_evidence_retention="—",
        audit_control_1="—",
        audit_control_2="—",
        closure_date=_dash_if_empty(date_str),
        confidence_level=confidence_level,
    )

    return md

