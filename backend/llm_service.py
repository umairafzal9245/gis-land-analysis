import os
import httpx
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

def get_gemini_response(prompt: str) -> str:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Gemini API key not found. Please add GEMINI_API_KEY to .env."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text

def get_groq_response(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Groq API key not found. Please add GROQ_API_KEY to .env."
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Groq Error: {e}"

def get_ollama_response(prompt: str) -> str:
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    payload = {"model": "llama3", "prompt": prompt, "stream": False}
    try:
        response = httpx.post(url, json=payload, timeout=120.0)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        return f"Ollama error: {e}"

def generate_report_prompt(stats: dict, extra_context: str = "", shop_size_m2: float = 120.0) -> str:
    main_breakdown = "\n".join([f"- {k}: {v}" for k, v in stats.get("mainlanduse_label", {}).items()])
    detail_breakdown = "\n".join([f"- {k}: {v}" for k, v in stats.get("landuse_category", {}).items()])
    subtypes = "\n".join([f"- {st}" for st in stats.get("subtypes", [])[:20]])
    
    prompt = f"""
You are an expert urban planner. Analyze the following GIS data and provide a report.

Tier 1: MAINLANDUSE Breakdown
{main_breakdown or 'None available'}

Tier 2: DETAILSLANDUSE Breakdown
{detail_breakdown or 'None available'}
Total Mosque Capacity (8 m2/person): {stats.get('total_mosque_capacity', 0)}
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
    prompt = generate_report_prompt(stats, extra_context, shop_size_m2)
    if provider == "gemini":
        return get_gemini_response(prompt)
    elif provider == "groq":
        return get_groq_response(prompt)
    else:
        return get_ollama_response(prompt)
