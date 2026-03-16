"""LLM service for generating analysis reports.

Supports multiple providers: Gemini, Groq, Ollama.
Generates reports from selection summaries with SUBTYPE-based breakdowns.
"""
import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")


# =============================================================================
# LLM Provider Functions
# =============================================================================


def get_gemini_response(prompt: str) -> str:
    """Generate response using Google Gemini."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Gemini API key not found. Please add GEMINI_API_KEY to .env."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text


def get_groq_response(prompt: str) -> str:
    """Generate response using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not found. Please add GROQ_API_KEY to .env."
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60.0
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Groq Error: {e}"


def get_ollama_response(prompt: str) -> str:
    """Generate response using local Ollama."""
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    try:
        response = httpx.post(url, json=payload, timeout=120.0)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Ollama error: {e}"


def call_llm(prompt: str, provider: str = LLM_PROVIDER) -> str:
    """Route prompt to the configured LLM provider."""
    if provider == "gemini":
        return get_gemini_response(prompt)
    elif provider == "groq":
        return get_groq_response(prompt)
    else:
        return get_ollama_response(prompt)


# =============================================================================
# Report Generation
# =============================================================================


def generate_selection_report(
    selection_summary: dict,
    extra_context: Optional[str] = None,
    provider: str = LLM_PROVIDER
) -> str:
    """Generate an LLM report from a polygon/bbox selection summary.
    
    The prompt uses SUBTYPE-based categorization with LANDUSE_CATEGORY breakdowns.
    
    Args:
        selection_summary: The breakdown object from polygon/bbox selection
        extra_context: Optional user-provided context
        provider: LLM provider to use (gemini, groq, ollama)
        
    Returns:
        Generated report text with five sections.
    """
    prompt = build_selection_report_prompt(selection_summary, extra_context)
    return call_llm(prompt, provider)


def build_selection_report_prompt(
    summary: dict,
    extra_context: Optional[str] = None
) -> str:
    """Build the LLM prompt for selection report generation.
    
    Report sections:
    1. Area Overview
    2. Land Use Analysis by Type
    3. Capacity and Utilization Assessment
    4. Development Status
    5. Recommendations
    """
    # Extract key metrics
    total_parcels = summary.get("total_parcels", 0)
    total_area_m2 = summary.get("total_area_m2", 0)
    vacant_count = summary.get("vacant_count", 0)
    developed_count = summary.get("developed_count", 0)
    commercial_area = summary.get("commercial_total_area_m2", 0)
    non_commercial_area = summary.get("non_commercial_total_area_m2", 0)
    religious_capacity = summary.get("total_religious_capacity", 0)
    shops_estimated = summary.get("total_shops_estimated", 0)
    blocks_covered = summary.get("block_ids_covered", [])
    
    # Build category breakdown section
    breakdown = summary.get("breakdown", {})
    category_lines = []
    for category, data in breakdown.items():
        count = data.get("count", 0)
        area = data.get("total_area_m2", 0)
        capacity = data.get("total_capacity_estimated", 0)
        shops = data.get("total_shops_estimated", 0)
        
        line = f"  - {category}: {count} parcels, {area:,.0f} m²"
        if capacity > 0:
            line += f", capacity: {capacity:,}"
        if shops > 0:
            line += f", shops: {shops:,}"
        category_lines.append(line)
    
    category_breakdown_text = "\n".join(category_lines) if category_lines else "  No data available"
    
    # Build vacancy analysis
    if total_parcels > 0:
        vacancy_rate = (vacant_count / total_parcels) * 100
        development_rate = (developed_count / total_parcels) * 100
    else:
        vacancy_rate = 0
        development_rate = 0
    
    vacancy_text = f"""
  - Vacant Parcels: {vacant_count} ({vacancy_rate:.1f}%)
  - Developed Parcels: {developed_count} ({development_rate:.1f}%)
  - Other Status: {total_parcels - vacant_count - developed_count} parcels"""
    
    # Build blocks section
    blocks_text = ", ".join(blocks_covered[:10]) if blocks_covered else "None identified"
    if len(blocks_covered) > 10:
        blocks_text += f" ... and {len(blocks_covered) - 10} more"
    
    prompt = f"""You are an expert urban planner analyzing a land parcel selection in Saudi Arabia.

=== SELECTION DATA ===

AREA OVERVIEW:
  - Total Parcels: {total_parcels}
  - Total Area: {total_area_m2:,.0f} m²
  - Commercial Area: {commercial_area:,.0f} m²
  - Non-Commercial Area: {non_commercial_area:,.0f} m²
  - Blocks Covered: {blocks_text}

LAND USE BREAKDOWN BY CATEGORY (SUBTYPE-based classification):
{category_breakdown_text}

CAPACITY ESTIMATES:
  - Total Religious Facility Capacity: {religious_capacity:,} worshippers (at 1 m²/person)
  - Total Commercial Shops: {shops_estimated:,} units (at 120 m²/shop estimate)

DEVELOPMENT STATUS:
{vacancy_text}

"""
    
    if extra_context:
        prompt += f"""ADDITIONAL CONTEXT FROM USER:
{extra_context}

"""
    
    prompt += """=== INSTRUCTIONS ===

Generate a professional urban planning report with EXACTLY these five sections:

1. AREA OVERVIEW
   Summarize the selection: total parcels, total area, number of blocks covered.

2. LAND USE ANALYSIS BY TYPE
   Analyze each LANDUSE_CATEGORY present. Use specific SUBTYPE labels where relevant.
   Discuss the distribution and any notable patterns.

3. CAPACITY AND UTILIZATION ASSESSMENT
   Evaluate religious facility (mosque) capacity relative to population estimates.
   Analyze commercial potential and shop density.
   Identify any capacity constraints or opportunities.

4. DEVELOPMENT STATUS
   Analyze vacancy rates and development levels.
   Highlight areas with high vacancy or underutilization.

5. RECOMMENDATIONS
   Provide 3-5 actionable recommendations for urban planners.
   Consider zoning, development priorities, and infrastructure needs.

Write in a professional, objective tone. Use numbers and percentages to support analysis.
Do NOT add any sections beyond the five listed above.
"""
    
    return prompt


# =============================================================================
# Legacy Functions (backward compatibility)
# =============================================================================


def generate_report_prompt(stats: dict, extra_context: str = "", shop_size_m2: float = 120.0) -> str:
    """Legacy prompt generation function."""
    main_breakdown = "\n".join([f"- {k}: {v}" for k, v in stats.get("mainlanduse_label", {}).items()])
    detail_breakdown = "\n".join([f"- {k}: {v}" for k, v in stats.get("landuse_category", {}).items()])
    subtypes = "\n".join([f"- {st}" for st in stats.get("subtypes", [])[:20]])
    
    prompt = f"""
You are an expert urban planner. Analyze the following GIS data and provide a report.

Tier 1: MAINLANDUSE Breakdown
{main_breakdown or 'None available'}

Tier 2: DETAILSLANDUSE Breakdown
{detail_breakdown or 'None available'}
Total Mosque Capacity (1 m2/person): {stats.get('total_religious_capacity', 0)}
Total Shops ({shop_size_m2} m2/shop): {stats.get('total_shops', 0)}

Tier 3: SUBTYPE Summary
{subtypes or 'None available'}

Development Status:
Vacant Parcels: {stats.get('vacant_count', 0)}
Developed Parcels: {stats.get('developed_count', 0)}

Total Area: {stats.get('total_area_m2', 0)} m2
Total Parcels: {stats.get('total_parcels', 0)}

Additional Context:
{extra_context}

Please provide the report exactly in these seven sections:
1. Executive Summary
2. Land Use Distribution by MAINLANDUSE category
3. Detailed Breakdown by DETAILSLANDUSE type
4. Commercial Utilization Assessment
5. Mosque and Public Facility Capacity Review
6. Development Status and Vacancy Analysis
7. Recommendations for Urban Planners
"""
    return prompt


def analyze_parcels(stats: dict, provider: str = LLM_PROVIDER, extra_context: str = "", shop_size_m2: float = 120.0) -> str:
    """Legacy function: Generate report from stats dict."""
    prompt = generate_report_prompt(stats, extra_context, shop_size_m2)
    return call_llm(prompt, provider)


def analyze_single_mosque(object_id: int, provider: str = LLM_PROVIDER) -> str:
    """Legacy function: Generate brief analysis for a single mosque parcel."""
    prompt = f"Please provide a short paragraph about the mosque parcel with OBJECTID {object_id}, its capacity, its location context, and how it compares to the neighbourhood average."
    return call_llm(prompt, provider)
