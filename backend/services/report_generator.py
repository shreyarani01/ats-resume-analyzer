import os
import logging
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from typing import Dict, Any

logger = logging.getLogger("ats_resume_scorer")

# Absolute path resolution to project root templates directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def format_date(value, fmt='%B %d, %Y at %I:%M %p'):
    """Convert ISO timestamp string → human-readable date string."""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime(fmt)
    except Exception:
        return str(value)

env.filters['format_date'] = format_date


def _to_dict(item: Any) -> Any:
    """Helper to safely dump Pydantic objects or dicts recursively."""
    if hasattr(item, 'model_dump'):
        return item.model_dump()
    elif isinstance(item, dict):
        return {k: _to_dict(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [_to_dict(i) for i in item]
    return item


def generate_html_reports(analysis_data: Dict[str, Any]) -> Dict[str, str]:
    # Ensure analysis_data is standard dict
    analysis_data = _to_dict(analysis_data) or {}

    now = datetime.now(timezone.utc).isoformat()

    # Overall score & interpretation
    overall_score = float(analysis_data.get('ATS_score', 0) or analysis_data.get('ats_score', 0))
    interpretation = analysis_data.get('interpretation', '')  
    
    cs = analysis_data.get('component_scores', {}) or {}

    component_scores = {
        'formatting':       float(cs.get('formatting', 0)),
        'keywords':         float(cs.get('keywords', 0)),
        'content':          float(cs.get('content', 0)),
        'skill_validation': float(cs.get('skill_validation', 0)),
        'ats_compatibility': float(cs.get('ats_compatibility', 0)),
    }

    def pct(score, max_score):
        if max_score <= 0:
            return 0
        return min(100, max(0, round(score / max_score * 100)))

    component_pct = {
        'formatting':       pct(component_scores['formatting'],       20),
        'keywords':         pct(component_scores['keywords'],         25),
        'content':          pct(component_scores['content'],          25),
        'skill_validation': pct(component_scores['skill_validation'], 15),
        'ats_compatibility': pct(component_scores['ats_compatibility'], 15),
    }

    detailed_feedback = _to_dict(analysis_data.get('detailed_feedback', []))

    high_priority = [fb for fb in detailed_feedback if str(fb.get('severity_level', '')).lower() in ('high',)]
    medium_priority = [fb for fb in detailed_feedback if str(fb.get('severity_level', '')).lower() in ('moderate', 'medium')]
    low_priority = [fb for fb in detailed_feedback if str(fb.get('severity_level', '')).lower() in ('low', 'info')]

    strengths = analysis_data.get('strengths', [])

    svd_raw = _to_dict(analysis_data.get('skill_validation_details', {}) or {})
    validated_skills = svd_raw.get('validated', [])
    unvalidated_skills = svd_raw.get('unvalidated', [])
    total_skills = svd_raw.get('total', len(validated_skills) + len(unvalidated_skills))
    validated_count = svd_raw.get('validated_count', len(validated_skills))
    validation_pct = svd_raw.get('validation_pct', 0.0)

    jd_raw = _to_dict(analysis_data.get('jd_match_analysis') or analysis_data.get('jd_comparison') or {})

    # Color thresholding
    if overall_score >= 80:
        score_color = '#16a34a'   # Green
    elif overall_score >= 60:
        score_color = '#d97706'   # Amber
    else:
        score_color = '#dc2626'   # Red

    context = {
        'timestamp':          now,
        'overall_score':      overall_score,
        'score_color':        score_color,
        'interpretation':     interpretation,
        'component_scores':   component_scores,
        'component_pct':      component_pct,
        'strengths':          strengths,
        'high_priority':      high_priority,
        'medium_priority':    medium_priority,
        'low_priority':       low_priority,
        'all_feedback':       detailed_feedback,
        'validated_skills':   validated_skills,
        'unvalidated_skills': unvalidated_skills,
        'total_skills':       total_skills,
        'validated_count':    validated_count,
        'validation_pct':     validation_pct,
        'jd_analysis':        jd_raw,
    }

    reports = {}
    
    # Safely load and render each template
    template_mapping = {
        'summary': 'summary.html',
        'skill_report': 'action.html',
        'jd_report': 'quick_act.html',
        'recommendations': 'jd_comp.html',
    }

    for report_key, template_name in template_mapping.items():
        try:
            tmpl = env.get_template(template_name)
            reports[report_key] = tmpl.render(**context)
        except TemplateNotFound:
            logger.error(f"Template '{template_name}' not found in directory: {TEMPLATE_DIR}")
            reports[report_key] = f"<!-- Template {template_name} missing -->"
        except Exception as err:
            logger.error(f"Failed to render template '{template_name}': {err}")
            reports[report_key] = f"<!-- Error rendering {template_name}: {err} -->"

    return reports