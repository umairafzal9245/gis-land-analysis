"""LLM service for generating analysis reports.

Supports multiple providers: Gemini, Groq, Ollama.
Generates reports from selection summaries with SUBTYPE-based breakdowns.
"""
import json
import os
import re
import httpx
from typing import Optional, AsyncIterator
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
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"


async def stream_gemini_response(prompt: str) -> AsyncIterator[str]:
    """Stream response from Google Gemini token by token."""
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        yield "Gemini API key not found. Please add GEMINI_API_KEY to .env."
        return
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"Gemini Error: {e}"


def get_groq_response(prompt: str) -> str:
    """Generate response using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not found. Please add GROQ_API_KEY to .env."
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
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


async def stream_groq_response(prompt: str) -> AsyncIterator[str]:
    """Stream response from Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        yield "Groq API key not found. Please add GROQ_API_KEY to .env."
        return
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
    except Exception as e:
        yield f"Groq Error: {e}"


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


async def stream_ollama_response(prompt: str) -> AsyncIterator[str]:
    """Stream response from local Ollama."""
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    payload = {"model": "llama3", "prompt": prompt, "stream": True}
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST", url, json=payload, timeout=120.0
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"Ollama error: {e}"


def call_llm(prompt: str, provider: str = LLM_PROVIDER) -> str:
    """Route prompt to the configured LLM provider, with automatic fallback."""
    providers = _provider_order(provider)
    last_error = None
    for p in providers:
        try:
            if p == "gemini":
                result = get_gemini_response(prompt)
            elif p == "groq":
                result = get_groq_response(prompt)
            else:
                result = get_ollama_response(prompt)
            # Treat error-message returns as failures to trigger fallback
            if result.startswith(("Gemini API key not found", "Groq API key not found",
                                  "Groq Error:", "Gemini Error:", "Ollama error:")):
                last_error = result
                continue
            return result
        except Exception as e:
            last_error = str(e)
            continue
    return f"All LLM providers failed. Last error: {last_error}"


async def stream_llm(prompt: str, provider: str = LLM_PROVIDER) -> AsyncIterator[str]:
    """Route prompt to the configured LLM provider with streaming and fallback."""
    providers = _provider_order(provider)
    for p in providers:
        try:
            chunks = []
            failed = False
            if p == "gemini":
                gen = stream_gemini_response(prompt)
            elif p == "groq":
                gen = stream_groq_response(prompt)
            else:
                gen = stream_ollama_response(prompt)
            async for chunk in gen:
                # Detect error messages in first chunk
                if not chunks and chunk.startswith((
                    "Gemini API key not found", "Groq API key not found",
                    "Groq Error:", "Gemini Error:", "Ollama error:",
                )):
                    failed = True
                    break
                chunks.append(chunk)
                yield chunk
            if not failed and chunks:
                return  # success
        except Exception:
            continue
    if not chunks:
        yield "All LLM providers failed. Please check your API keys."


def _provider_order(primary: str) -> list[str]:
    """Return provider list with primary first, then fallbacks."""
    all_providers = ["gemini", "groq", "ollama"]
    if primary in all_providers:
        all_providers.remove(primary)
    return [primary] + all_providers


# =============================================================================
# Report Generation
# =============================================================================


def generate_selection_report(
    selection_summary: dict,
    extra_context: Optional[str] = None,
    filtered_summary: Optional[dict] = None,
    applied_filters: Optional[list] = None,
    capacity_calculations: Optional[list] = None,
    report_type: str = "selection",
    report_title: Optional[str] = None,
    provider: str = LLM_PROVIDER,
) -> str:
    """Generate an LLM report from a polygon/bbox selection summary.

    Uses all available user-session context (filters, capacity calculations, etc.)
    to produce a factually accurate, context-specific report.

    Args:
        selection_summary: The full breakdown object from polygon/bbox selection.
        extra_context: Optional user-provided context text.
        filtered_summary: Optional pre-computed stats for the filtered subset.
        applied_filters: Optional list of human-readable filter descriptions.
        capacity_calculations: Optional list of individual capacity calc results.
        report_type: One of 'selection', 'filtered', 'block'.
        report_title: Optional custom title for the report.
        provider: LLM provider to use (gemini, groq, ollama).

    Returns:
        Generated report text.
    """
    prompt = build_selection_report_prompt(
        summary=selection_summary,
        extra_context=extra_context,
        filtered_summary=filtered_summary,
        applied_filters=applied_filters,
        capacity_calculations=capacity_calculations,
        report_type=report_type,
        report_title=report_title,
    )
    return call_llm(prompt, provider)


def build_selection_report_prompt(
    summary: dict,
    extra_context: Optional[str] = None,
    filtered_summary: Optional[dict] = None,
    applied_filters: Optional[list] = None,
    capacity_calculations: Optional[list] = None,
    report_type: str = "selection",
    report_title: Optional[str] = None,
) -> str:
    """Build a context-aware LLM prompt for report generation.

    The prompt embeds ONLY the exact data provided — no estimates or invented
    numbers are included.  The LLM is explicitly instructed to reproduce
    only those numbers in its output.
    """
    title = report_title or "GIS Land Analysis Report"

    # ---- Initial selection metrics ----
    total_parcels = summary.get("total_parcels", 0)
    total_area_m2 = summary.get("total_area_m2", 0)
    vacant_count = summary.get("vacant_count", 0)
    developed_count = summary.get("developed_count", 0)
    religious_capacity = summary.get("total_religious_capacity", 0)
    shops_estimated = summary.get("total_shops_estimated", 0)
    blocks_covered = summary.get("block_ids_covered", [])
    breakdown = summary.get("breakdown", {})

    vacancy_rate = (vacant_count / total_parcels * 100) if total_parcels > 0 else 0.0
    dev_rate = (developed_count / total_parcels * 100) if total_parcels > 0 else 0.0

    blocks_text = ", ".join(str(b) for b in blocks_covered[:10]) if blocks_covered else "None identified"
    if len(blocks_covered) > 10:
        blocks_text += f" (and {len(blocks_covered) - 10} more)"

    # ---- Assemble prompt header ----
    prompt = f"""You are an expert urban planner producing a professional GIS land analysis report for a project in Saudi Arabia.

REPORT TYPE: {report_type.upper()}
REPORT TITLE: {title}

=== INITIAL AREA SELECTION ===
Total Parcels: {total_parcels:,}
Total Area: {total_area_m2:,.0f} m² ({total_area_m2 / 10_000:.2f} hectares)
Blocks Covered: {blocks_text} ({len(blocks_covered)} block(s))
Vacant Parcels: {vacant_count:,} ({vacancy_rate:.1f}%)
Developed Parcels: {developed_count:,} ({dev_rate:.1f}%)
"""

    if religious_capacity > 0:
        prompt += f"Total Religious Facility Capacity: {religious_capacity:,} worshippers\n"
    if shops_estimated > 0:
        prompt += f"Total Estimated Commercial Shops: {shops_estimated:,} units\n"

    # ---- Full selection land-use breakdown ----
    if breakdown:
        prompt += "\nLAND USE BREAKDOWN (Full Selection):\n"
        for cat, data in sorted(breakdown.items(), key=lambda x: x[1].get("count", 0), reverse=True):
            count = data.get("count", 0)
            area = data.get("total_area_m2", 0)
            cap = data.get("total_capacity_estimated", 0)
            shops = data.get("total_shops_estimated", 0)
            line = f"  - {cat}: {count} parcels, {area:,.0f} m²"
            if cap > 0:
                line += f" | capacity: {cap:,} worshippers"
            if shops > 0:
                line += f" | estimated shops: {shops:,}"
            prompt += line + "\n"

    # ---- Applied filters ----
    if applied_filters:
        prompt += "\n=== APPLIED FILTERS / QUERIES ===\n"
        for f_desc in applied_filters:
            prompt += f"  - {f_desc}\n"

    # ---- Filtered/queried subset ----
    if filtered_summary:
        f_total = filtered_summary.get("total_parcels", 0)
        f_area = filtered_summary.get("total_area_m2", 0)
        f_vacant = filtered_summary.get("vacant_count", 0)
        f_developed = filtered_summary.get("developed_count", 0)
        f_blocks = filtered_summary.get("block_ids_covered", [])
        f_breakdown = filtered_summary.get("breakdown", {})
        f_vacancy = (f_vacant / f_total * 100) if f_total > 0 else 0.0

        prompt += f"""
=== FILTERED SELECTION — PRIMARY ANALYSIS TARGET ===
Filtered Parcels: {f_total:,} out of {total_parcels:,} total ({f_total / total_parcels * 100:.1f}%)
Filtered Area: {f_area:,.0f} m² ({f_area / 10_000:.2f} hectares)
Vacant: {f_vacant:,} ({f_vacancy:.1f}%) | Developed: {f_developed:,}
Blocks in Filtered Set: {", ".join(str(b) for b in f_blocks[:8])} ({len(f_blocks)} block(s))
"""
        if f_breakdown:
            prompt += "Filtered Land Use Breakdown:\n"
            for cat, data in sorted(f_breakdown.items(),
                                    key=lambda x: x[1].get("count", 0) if isinstance(x[1], dict) else 0,
                                    reverse=True):
                if not isinstance(data, dict):
                    continue
                count = data.get("count", 0)
                area = data.get("total_area_m2", 0)
                subtypes = data.get("subtypes", {})
                line = f"  - {cat}: {count} parcels, {area:,.0f} m²"
                if subtypes:
                    top = sorted(subtypes.items(), key=lambda x: x[1], reverse=True)[:3]
                    line += f" (subtypes: {', '.join(f'{s}: {c}' for s, c in top)})"
                prompt += line + "\n"

    # ---- Individual capacity calculations ----
    if capacity_calculations:
        prompt += "\n=== CAPACITY CALCULATIONS PERFORMED BY USER ===\n"
        for calc in capacity_calculations:
            ctype = calc.get("type", "unknown")
            pid = calc.get("parcel_id", "N/A")
            subtype = calc.get("subtype", "Unknown")
            area_m2 = calc.get("area_m2", 0)
            if ctype == "mosque":
                cap_val = calc.get("capacity_worshippers", 0)
                rate = calc.get("rate_m2_per_worshipper", 8.0)
                floors = calc.get("floors_estimated", 1)
                prompt += (
                    f"  - Mosque: {subtype} (ID: {pid}) | "
                    f"{area_m2:,.0f} m² | {floors} floor(s) | "
                    f"Capacity: {cap_val:,} worshippers @ {rate} m²/worshipper\n"
                )
            elif ctype == "commercial":
                shops = calc.get("shops_estimated", 0)
                shop_size = calc.get("shop_size_m2", 120)
                floors = calc.get("floors_estimated", 1)
                prompt += (
                    f"  - Commercial: {subtype} (ID: {pid}) | "
                    f"{area_m2:,.0f} m² | {floors} floor(s) | "
                    f"Estimated {shops:,} shops @ {shop_size} m²/shop\n"
                )

    # ---- Extra user context ----
    if extra_context:
        prompt += f"\n=== ADDITIONAL CONTEXT FROM USER ===\n{extra_context}\n"

    # ---- Section structure based on report type ----
    has_filter = filtered_summary is not None
    has_capacity = bool(capacity_calculations)

    if report_type == "block":
        analysis_section = (
            "3. BLOCK COMPOSITION\n"
            "   Analyze the land use mix within this specific block. List every category present\n"
            "   with exact parcel counts and areas from the data."
        )
    elif has_filter:
        analysis_section = (
            "3. FILTERED AREA ANALYSIS\n"
            "   Deep-dive into the FILTERED SELECTION.  List every land-use type with exact\n"
            "   counts, areas, and notable subtypes.  Compare proportions to the full selection\n"
            "   where this adds insight."
        )
    else:
        analysis_section = (
            "3. LAND USE ANALYSIS\n"
            "   Analyze every LANDUSE_CATEGORY present.  Use exact counts and areas from the\n"
            "   data.  Discuss distribution and notable patterns."
        )

    capacity_section_text = ""
    next_section = 4
    if has_capacity:
        capacity_section_text = (
            "4. CAPACITY ASSESSMENT\n"
            "   For each parcel capacity calculation listed above, state the exact result.\n"
            "   Contextualise: is this capacity adequate for the surrounding land use?\n"
            "   Compare individual results to the aggregate figures in the selection.\n"
        )
        next_section = 5

    prompt += f"""
=== REPORT INSTRUCTIONS ===

Generate a professional urban planning report with EXACTLY the sections below.

CRITICAL RULE: Every number you cite in the report MUST match the data supplied above exactly.
Do NOT invent, round, or approximate any figure that is not in the data.
Do NOT add sections beyond those listed.

1. EXECUTIVE SUMMARY
   2–3 sentences: what area was selected, any filters or queries applied, and the single most
   important finding.

2. AREA OVERVIEW
   Report exact figures: total parcels, total area (m² and hectares), blocks covered,
   vacant count and percentage, developed count and percentage.
   {"If a filtered subset is present, summarise both the full selection and the filtered focus area." if has_filter else ""}

{analysis_section}

{capacity_section_text}
{next_section}. DEVELOPMENT STATUS
   Use the exact vacancy and development numbers. Identify concerns or opportunities
   (e.g., high vacancy in a specific category, underdeveloped commercial land).

{next_section + 1}. RECOMMENDATIONS
   Provide 3–5 specific, actionable recommendations for urban planners.
   Reference actual categories, block IDs, and numbers from the data.

Write in a formal, objective tone suitable for a planning authority submission.
"""
    return prompt


# =============================================================================
# Natural Language Query
# =============================================================================


def answer_nl_query(
    question: str,
    parcels_summary: dict,
    provider: str = LLM_PROVIDER,
) -> dict:
    """Answer a natural language question about parcels in a selection.

    Args:
        question: The user's question in natural language.
        parcels_summary: Compact summary of the parcels (counts, areas, categories).
        provider: LLM provider to use.

    Returns:
        Dict with 'answer' text and 'matching_parcel_ids' list.
    """
    prompt = _build_nl_query_prompt(question, parcels_summary)
    raw = call_llm(prompt, provider)
    answer, filters = _parse_nl_response(raw)
    matching_ids = _filter_parcels_by_criteria(parcels_summary.get("parcels", []), filters)

    # Patch: Ensure answer count matches filtered result
    import re
    count = len(matching_ids)
    patched_answer = answer
    # Try to replace any leading count in the answer (e.g., "19 commercial parcels ...")
    patched = False
    m = re.match(r"(\d+)\s+([a-zA-Z\s]+parcels? can fit.*)", answer.strip(), re.IGNORECASE)
    if m:
        patched_answer = f"{count} {m.group(2)}"
        patched = True
    # If not patched, append a clarifying line
    if not patched:
        patched_answer = answer.strip()
        if not patched_answer.endswith("."):
            patched_answer += "."
        patched_answer += f" (Actual matching parcels: {count})"

    return {"answer": patched_answer, "matching_parcel_ids": matching_ids}


async def stream_nl_query(
    question: str,
    parcels_summary: dict,
    provider: str = LLM_PROVIDER,
) -> AsyncIterator[str]:
    """Stream an NL query answer as SSE events.

    Streams the answer text token-by-token, then sends a final event
    with the matching parcel IDs (extracted from the accumulated response).
    """
    prompt = _build_nl_query_prompt(question, parcels_summary)
    full_response = ""
    async for chunk in stream_llm(prompt, provider):
        full_response += chunk
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

    # Parse filters from the complete response
    answer, filters = _parse_nl_response(full_response)
    matching_ids = _filter_parcels_by_criteria(
        parcels_summary.get("parcels", []), filters
    )
    yield f"data: {json.dumps({'type': 'done', 'matching_parcel_ids': matching_ids})}\n\n"


def _build_nl_query_prompt(question: str, summary: dict) -> str:
    total_parcels = summary.get("total_parcels", 0)
    total_area = summary.get("total_area_m2", 0)
    vacant = summary.get("vacant_count", 0)
    developed = summary.get("developed_count", 0)
    breakdown = summary.get("category_breakdown", {})
    religious_capacity = summary.get("total_religious_capacity", 0)
    shops_estimated = summary.get("total_shops_estimated", 0)
    commercial_area = summary.get("commercial_total_area_m2", 0)
    non_commercial_area = summary.get("non_commercial_total_area_m2", 0)

    cat_lines = "\n".join(
        f"  - {cat}: {cnt} parcels"
        for cat, cnt in sorted(breakdown.items(), key=lambda x: -x[1])
    ) or "  No category data available"

    # Build rich breakdowns from parcels list
    parcels = summary.get("parcels", [])
    subtype_counts: dict[str, int] = {}
    detail_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    commercial_count = 0
    non_commercial_count = 0
    floor_counts: dict[str, int] = {}
    areas: list[float] = []

    for p in parcels:
        # Subtype & Detail
        st = p.get("SUBTYPE_LABEL_EN") or p.get("SUBTYPE") or "Unknown"
        dt = p.get("DETAIL_LABEL_EN") or p.get("DETAILSLANDUSE") or "Unknown"
        subtype_counts[st] = subtype_counts.get(st, 0) + 1
        detail_counts[dt] = detail_counts.get(dt, 0) + 1

        # Development / Parcel status
        status = p.get("PARCEL_STATUS_LABEL") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

        # Commercial vs Non-Commercial
        is_comm = p.get("IS_COMMERCIAL")
        if is_comm == 1 or is_comm is True or str(is_comm).lower() == "true":
            commercial_count += 1
        else:
            non_commercial_count += 1

        # Floors
        floors = p.get("NOOFFLOORS")
        if floors and float(floors) > 0:
            floor_label = f"{int(float(floors))} floor(s)"
            floor_counts[floor_label] = floor_counts.get(floor_label, 0) + 1

        # Area
        area = float(p.get("AREA_M2") or 0)
        if area > 0:
            areas.append(area)

    subtype_lines = "\n".join(
        f"  - {st}: {cnt} parcels"
        for st, cnt in sorted(subtype_counts.items(), key=lambda x: -x[1])
    ) or "  No subtype data available"

    detail_lines = "\n".join(
        f"  - {dt}: {cnt} parcels"
        for dt, cnt in sorted(detail_counts.items(), key=lambda x: -x[1])
    ) or "  No detail data available"

    status_lines = "\n".join(
        f"  - {s}: {cnt} parcels"
        for s, cnt in sorted(status_counts.items(), key=lambda x: -x[1])
    ) or "  No status data available"

    floor_lines = "\n".join(
        f"  - {fl}: {cnt} parcels"
        for fl, cnt in sorted(floor_counts.items(), key=lambda x: -x[1])
    ) or "  No floor data available"

    area_stats = ""
    if areas:
        area_stats = (
            f"  Smallest Parcel: {min(areas):,.0f} m²\n"
            f"  Largest Parcel: {max(areas):,.0f} m²\n"
            f"  Average Parcel Size: {sum(areas) / len(areas):,.0f} m²"
        )
    else:
        area_stats = "  No area data available"

    # ---- Numeric distributions for threshold queries ----
    capacity_values = []
    shops_values = []
    for p in parcels:
        cap = float(p.get("CAPACITY_ESTIMATED") or 0)
        if cap > 0:
            capacity_values.append(cap)
        shp = float(p.get("SHOPS_ESTIMATED") or 0)
        if shp > 0:
            shops_values.append(shp)

    # Area distribution buckets
    area_buckets = [
        ("< 500 m²",         lambda a: a < 500),
        ("500–1,000 m²",     lambda a: 500 <= a < 1000),
        ("1,000–2,000 m²",   lambda a: 1000 <= a < 2000),
        ("2,000–5,000 m²",   lambda a: 2000 <= a < 5000),
        ("> 5,000 m²",       lambda a: a >= 5000),
    ]
    area_dist_lines = "\n".join(
        f"  {label}: {sum(1 for a in areas if fn(a))} parcels"
        for label, fn in area_buckets
    ) if areas else "  No area data available"

    # Capacity distribution (religious/mosque parcels only)
    if capacity_values:
        cap_thresholds = [100, 250, 350, 500, 750, 1000]
        cap_dist_lines = "\n".join(
            f"  > {t}: {sum(1 for c in capacity_values if c > t)} parcels"
            for t in cap_thresholds
        )
        cap_dist_lines = (
            f"  Total with capacity > 0: {len(capacity_values)} parcels\n"
            f"  Min: {min(capacity_values):,.0f}  Max: {max(capacity_values):,.0f}  "
            f"Avg: {sum(capacity_values)/len(capacity_values):,.0f}\n"
            + cap_dist_lines
        )
    else:
        cap_dist_lines = "  No capacity data available"

    # Shops distribution (commercial parcels only)
    if shops_values:
        shop_thresholds = [5, 10, 15, 20, 30]
        shop_dist_lines = "\n".join(
            f"  > {t} shops: {sum(1 for s in shops_values if s > t)} parcels"
            for t in shop_thresholds
        )
        shop_dist_lines = (
            f"  Total with shops > 0: {len(shops_values)} parcels\n"
            f"  Max: {max(shops_values):,.0f}\n"
            + shop_dist_lines
        )
    else:
        shop_dist_lines = "  No shops data available"

    return f"""You are a GIS data assistant. Answer the user's question using ONLY the data provided below.
If the data does not contain information to answer the question, say so honestly — do NOT make up data.
Be concise and factual. Use numbers when available.

=== SELECTION DATA ===
Total Parcels: {total_parcels}
Total Area: {total_area:,.0f} m²

Development Status:
{status_lines}

Commercial: {commercial_count} parcels ({commercial_area:,.0f} m²)
Non-Commercial: {non_commercial_count} parcels ({non_commercial_area:,.0f} m²)

Estimated Religious/Mosque Capacity: {religious_capacity:,} worshippers
Estimated Commercial Shops: {shops_estimated:,}

Land Use Categories:
{cat_lines}

Land Use Subtypes:
{subtype_lines}

Detailed Land Use:
{detail_lines}

Building Floors Distribution:
{floor_lines}

Area Statistics:
{area_stats}

Area Distribution (all parcels):
{area_dist_lines}

Capacity Distribution (CAPACITY_ESTIMATED — religious/mosque parcels):
{cap_dist_lines}

Shops Distribution (SHOPS_ESTIMATED — commercial parcels):
{shop_dist_lines}

=== USER QUESTION ===
{question}

=== INSTRUCTIONS ===
Answer the question directly. If the answer can be derived from the data, provide it with numbers.
If the data does not have the information, respond: "This information is not available in the current selection data."
Do not hallucinate or invent numbers.

After your answer, on a NEW line, output a JSON block wrapped in ```json ... ``` with the following structure to indicate which parcels are relevant to your answer:
{{
  "relevant_categories": ["LANDUSE_CATEGORY values — use ONLY for broad queries like 'show all religious' or 'show commercial'"],
  "relevant_subtypes": ["SUBTYPE_LABEL_EN values if the question targets a subtype"],
  "relevant_details": ["DETAIL_LABEL_EN values from the Detailed Land Use section — use for SPECIFIC types like Mosque, School, Park, Hospital etc."],
  "relevant_statuses": ["STATUS values if the question targets development status e.g. Vacant, Developed"],
  "numeric_filters": [
    {{"field": "FIELD_NAME", "op": "OPERATOR", "value": NUMBER}}
  ]
}}
Available numeric fields:
  - "AREA_M2"            — parcel area in square metres (use the Area Distribution above for accurate counts)
  - "CAPACITY_ESTIMATED" — estimated worshipper capacity (religious parcels only; use the Capacity Distribution above)
  - "SHOPS_ESTIMATED"    — estimated number of commercial shop units (use the Shops Distribution above)
Supported operators: ">", "<", ">=", "<=", "="
IMPORTANT: Be as SPECIFIC as possible. Examples:
- "mosques with capacity > 350"              → relevant_details: ["Mosque"], numeric_filters: [{{"field": "CAPACITY_ESTIMATED", "op": ">", "value": 350}}]
- "vacant parcels larger than 2000 m²"       → relevant_statuses: ["Vacant"], numeric_filters: [{{"field": "AREA_M2", "op": ">", "value": 2000}}]
- "commercial parcels fitting > 10 shops"    → relevant_categories: ["Commercial"], numeric_filters: [{{"field": "SHOPS_ESTIMATED", "op": ">", "value": 10}}]
- "parcels between 1000 and 5000 m²"         → numeric_filters: [{{"field": "AREA_M2", "op": ">=", "value": 1000}}, {{"field": "AREA_M2", "op": "<=", "value": 5000}}]
- "schools with plot area under 800 m²"      → relevant_details: ["School"], numeric_filters: [{{"field": "AREA_M2", "op": "<", "value": 800}}]
- "how many mosques" (no threshold)          → relevant_details: ["Mosque"], numeric_filters: []
Only include non-empty arrays for criteria that are actually relevant to the question.
Omit "numeric_filters" or leave it empty when no numeric threshold is mentioned.
The label values MUST exactly match the labels from the data above (case-sensitive).
"""


def _parse_nl_response(raw: str) -> tuple[str, dict]:
    """Parse LLM response to extract the answer text and filter criteria JSON.

    Returns:
        Tuple of (answer_text, filters_dict).
    """
    filters = {}
    # Try to extract JSON block from ```json ... ```
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if json_match:
        try:
            filters = json.loads(json_match.group(1))
        except (json.JSONDecodeError, ValueError):
            filters = {}
        # Remove the JSON block from the answer
        answer = raw[:json_match.start()].strip()
    else:
        answer = raw.strip()
    return answer, filters


def _filter_parcels_by_criteria(parcels: list[dict], filters: dict) -> list[str]:
    """Filter parcels using criteria extracted from LLM response.

    Uses the most specific label filter available: details > subtypes > categories > statuses.
    Numeric filters (AREA_M2, CAPACITY_ESTIMATED, SHOPS_ESTIMATED) are applied as
    additional AND conditions on top of whatever label filter is active.

    Returns list of matching PARCEL_IDs.
    """
    categories = [v.lower() for v in filters.get("relevant_categories", [])]
    subtypes = [v.lower() for v in filters.get("relevant_subtypes", [])]
    details = [v.lower() for v in filters.get("relevant_details", [])]
    statuses = [v.lower() for v in filters.get("relevant_statuses", [])]
    numeric_filters = [
        nf for nf in filters.get("numeric_filters", [])
        if isinstance(nf, dict) and nf.get("field") and nf.get("op") and nf.get("value") is not None
    ]

    has_label_filter = any([categories, subtypes, details, statuses])
    has_numeric_filter = bool(numeric_filters)

    # If no filters at all, no highlighting
    if not has_label_filter and not has_numeric_filter:
        return []

    _OPS = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "=": lambda a, b: a == b,
        "==": lambda a, b: a == b,
    }

    def passes_numeric(p: dict) -> bool:
        for nf in numeric_filters:
            op_fn = _OPS.get(nf["op"])
            if op_fn is None:
                continue
            try:
                pval = float(p.get(nf["field"]) or 0)
                if not op_fn(pval, float(nf["value"])):
                    return False
            except (TypeError, ValueError):
                return False
        return True

    matched = []
    for p in parcels:
        # Determine label match (most specific wins)
        if has_label_filter:
            cat = (p.get("LANDUSE_CATEGORY") or "").lower()
            sub = (p.get("SUBTYPE_LABEL_EN") or "").lower()
            det = (p.get("DETAIL_LABEL_EN") or "").lower()
            sta = (p.get("PARCEL_STATUS_LABEL") or "").lower()

            if details:
                label_match = det in details
            elif subtypes:
                label_match = sub in subtypes
            elif categories:
                label_match = cat in categories
            else:
                label_match = sta in statuses
        else:
            label_match = True  # no label filter — numeric filter alone decides

        if label_match and passes_numeric(p):
            matched.append(str(p.get("PARCEL_ID")))

    return matched


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
Total Mosque Capacity (1.2 m2/person): {stats.get('total_religious_capacity', 0)}
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
