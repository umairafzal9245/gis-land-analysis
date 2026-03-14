import json

details_codes = [101011, 1001001, 405055, 5555, 303006, 306011, 401002, 303010, 303011, 405053, 101003, 207042, 301012, 301024, 301023, 101019, 301014, 405052, 405032, 201011, 304006, 303012, 303013, 302033]

subtypes = [101000, 1001000, 405000, 303000, 304000, 301000, 401000, 306000, 207000, 201000, 0, 302000]

main_uses = [100000, 1000000, 400000, 300000, 5555, 200000]

statuses = [0, 2, 1, 3, 8, 6]

def generate_details(code):
    code_str = str(code)
    if code_str.startswith('100'):
        return {"label_en": f"Commercial {code}", "label_ar": f"تجاري {code}", "category": "Commercial", "capacity_rate": 120, "unit": "m2/shop"}
    elif code_str.startswith('101'):
        return {"label_en": "Residential Villa" if code == 101011 else f"Residential {code}", "label_ar": "فيلا سكنية", "category": "Residential", "capacity_rate": 10, "unit": "m2/unit"}
    elif code_str.startswith('301'):
        return {"label_en": f"Mosque {code}", "label_ar": f"مسجد {code}", "category": "Mosque", "capacity_rate": 8, "unit": "m2/worshipper"}
    elif code_str.startswith('303') or code_str.startswith('304'):
        return {"label_en": f"Educational {code}", "label_ar": f"تعليمي {code}", "category": "Educational", "capacity_rate": 6, "unit": "m2/student"}
    elif code_str.startswith('306'):
        return {"label_en": f"Park {code}", "label_ar": f"حديقة {code}", "category": "Park", "capacity_rate": 15, "unit": "m2/visitor"}
    elif code_str.startswith('2'):
        return {"label_en": f"Industrial {code}", "label_ar": f"صناعي {code}", "category": "Industrial", "capacity_rate": 50, "unit": "m2/unit"}
    elif code_str.startswith('4'):
        return {"label_en": f"Commercial Sub {code}", "label_ar": f"تجاري فرعي {code}", "category": "Commercial", "capacity_rate": 120, "unit": "m2/shop"}
    else:
        return {"label_en": "Unknown", "label_ar": "غير معروف", "category": "Unknown", "capacity_rate": 0, "unit": "N/A"}

details_map = {code: generate_details(code) for code in details_codes}
subtype_map = {
    101000: {"label_en": "Villa", "label_ar": "فيلا"},
    1001000: {"label_en": "Commercial Unit", "label_ar": "وحدة تجارية"}
}

for code in subtypes:
    if code not in subtype_map:
        subtype_map[code] = {"label_en": f"Type {code}", "label_ar": f"النوع {code}"}

main_map = {
    100000: {"label_en": "Residential", "label_ar": "سكني"},
    1000000: {"label_en": "Commercial", "label_ar": "تجاري"},
    300000: {"label_en": "Public / Government", "label_ar": "حكومي / عام"},
    400000: {"label_en": "Commercial (sub)", "label_ar": "تجاري فرعي"},
    200000: {"label_en": "Industrial", "label_ar": "صناعي"},
    5555: {"label_en": "Unknown", "label_ar": "غير معروف"},
}

status_map = {
    0: "Vacant",
    2: "Developed",
    1: "Under Review",
    3: "Reserved",
    8: "Inactive",
    6: "Other"
}

with open("etl/constants.py", "w", encoding="utf-8") as f:
    f.write("METRIC_CRS = 'EPSG:32637'\n\n")
    f.write("DETAILSLANDUSE_MAP = \\\n")
    f.write(json.dumps(details_map, indent=4, ensure_ascii=False))
    f.write("\n\nSUBTYPE_MAP = \\\n")
    f.write(json.dumps(subtype_map, indent=4, ensure_ascii=False))
    f.write("\n\nMAINLANDUSE_MAP = \\\n")
    f.write(json.dumps(main_map, indent=4, ensure_ascii=False))
    f.write("\n\nPARCEL_STATUS_MAP = \\\n")
    f.write(json.dumps(status_map, indent=4, ensure_ascii=False))
    f.write("\n")
