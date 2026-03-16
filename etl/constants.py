"""ETL constants — single source of truth for all land-use domain mappings.

Numeric codes are stored exactly as they appear in the GDB:
  - MAINLANDUSE     : int    (e.g. 100000)
  - SUBTYPE         : int32  (e.g. 303000)
  - DETAILSLANDUSE  : float64 stored as int (e.g. 303006)  ← cast with int(float(v))

Three-level hierarchy:
  MAINLANDUSE (top grouping)
      └─ SUBTYPE (primary classification — single source of truth)
              └─ DETAILSLANDUSE (sub-category detail)

App-level LANDUSE_CATEGORY values — used in UI, queries, and block summaries:
  Residential | Commercial | Religious | Educational | Health |
  Municipal   | Recreational | Utilities | Special | Unknown
"""

# ---------------------------------------------------------------------------
# Coordinate Reference System
# ---------------------------------------------------------------------------
METRIC_CRS = "EPSG:32637"   # UTM zone 37N — metric CRS for Saudi Arabia

# ---------------------------------------------------------------------------
# App-level categories  (exhaustive list; used everywhere in the system)
# ---------------------------------------------------------------------------
LANDUSE_CATEGORIES = [
    "Residential",
    "Commercial",
    "Religious",
    "Educational",
    "Health",
    "Municipal",
    "Recreational",
    "Utilities",
    "Special",
    "Unknown",
]

# Alias kept for backward-compatibility with processor.py
QUERYABLE_CATEGORIES = LANDUSE_CATEGORIES

# ---------------------------------------------------------------------------
# PARCEL_STATUS_MAP  (PARCELSTATUS column)
# ---------------------------------------------------------------------------
PARCEL_STATUS_MAP = {
    0: "Vacant",
    1: "Under Construction",
    2: "Developed",
    3: "Reserved",
    6: "Planned",
    8: "Other",
}

# ---------------------------------------------------------------------------
# MAINLANDUSE_MAP — top-level land-use grouping
# Code pattern:  N00000  (100000, 200000 … 1000000)
# ---------------------------------------------------------------------------
MAINLANDUSE_MAP = {
    100000:  {"label_ar": "السكني",          "label_en": "Residential"},
    200000:  {"label_ar": "التجاري",         "label_en": "Commercial"},
    300000:  {"label_ar": "الخدمات العامة",  "label_en": "Public Services"},
    400000:  {"label_ar": "البنية التحتية",  "label_en": "Infrastructure"},
    1000000: {"label_ar": "استخدام خاص",     "label_en": "Special Use"},
    5555:    {"label_ar": "غير محدد",        "label_en": "Unclassified"},
}

# ---------------------------------------------------------------------------
# SUBTYPE_MAP — primary classification (single source of truth)
#
# Keys per entry:
#   label_ar        Arabic name exactly as used in the domain
#   label_en        English translation
#   main_category   App-level LANDUSE_CATEGORY (must be in LANDUSE_CATEGORIES)
#   main_cat_ar     Arabic label for the app category
#   is_commercial   True if this use generates commercial revenue
#   capacity_rate   m² per person/unit for capacity estimation (0 = N/A)
#   capacity_unit   Human-readable description of the capacity unit
# ---------------------------------------------------------------------------
SUBTYPE_MAP = {
    # ── Unclassified placeholder ─────────────────────────────────────────────
    0: {
        "label_ar": "غير محدد",
        "label_en": "Unclassified",
        "main_category": "Unknown",
        "main_cat_ar": "غير محدد",
        "is_commercial": False,
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Residential  (MAINLANDUSE 100000) ────────────────────────────────────
    101000: {
        "label_ar": "سكني",
        "label_en": "Residential",
        "main_category": "Residential",
        "main_cat_ar": "سكني",
        "is_commercial": False,
        "capacity_rate": 250,       # ~250 m² per residential villa unit
        "capacity_unit": "m² per unit",
    },

    # ── Commercial  (MAINLANDUSE 200000) ─────────────────────────────────────
    201000: {
        "label_ar": "محلات تجارية",
        "label_en": "Commercial Shops",
        "main_category": "Commercial",
        "main_cat_ar": "تجاري",
        "is_commercial": True,
        "capacity_rate": 50,        # ~50 m² per shop unit
        "capacity_unit": "m² per shop",
    },
    207000: {
        "label_ar": "خدمات تجارية أخرى",
        "label_en": "Other Commercial Services",
        "main_category": "Commercial",
        "main_cat_ar": "تجاري",
        "is_commercial": True,
        "capacity_rate": 50,
        "capacity_unit": "m² per shop",
    },

    # ── Public Services — Educational  (MAINLANDUSE 300000) ──────────────────
    301000: {
        "label_ar": "خدمات تعليمية",
        "label_en": "Educational Services",
        "main_category": "Educational",
        "main_cat_ar": "تعليمي",
        "is_commercial": False,
        "capacity_rate": 5,         # ~5 m² per student (mixed school types)
        "capacity_unit": "m² per student",
    },

    # ── Public Services — Health  (MAINLANDUSE 300000) ───────────────────────
    302000: {
        "label_ar": "خدمات صحية",
        "label_en": "Health Services",
        "main_category": "Health",
        "main_cat_ar": "صحي",
        "is_commercial": False,
        "capacity_rate": 20,        # ~20 m² per patient
        "capacity_unit": "m² per patient",
    },

    # ── Public Services — Religious  (MAINLANDUSE 300000) ────────────────────
    303000: {
        "label_ar": "خدمات دينية",
        "label_en": "Religious Services",
        "main_category": "Religious",
        "main_cat_ar": "ديني",
        "is_commercial": False,
        "capacity_rate": 1,         # ~1 m² per worshipper (prayer density)
        "capacity_unit": "m² per worshipper",
    },

    # ── Public Services — Municipal  (MAINLANDUSE 300000) ────────────────────
    304000: {
        "label_ar": "خدمات بلدية",
        "label_en": "Municipal Services",
        "main_category": "Municipal",
        "main_cat_ar": "بلدي",
        "is_commercial": False,
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Public Services — Recreational  (MAINLANDUSE 300000) ─────────────────
    306000: {
        "label_ar": "خدمات ترويحية",
        "label_en": "Recreational Services",
        "main_category": "Recreational",
        "main_cat_ar": "ترويحي",
        "is_commercial": False,
        "capacity_rate": 10,        # ~10 m² per visitor
        "capacity_unit": "m² per visitor",
    },

    # ── Infrastructure — Electricity  (MAINLANDUSE 400000) ───────────────────
    401000: {
        "label_ar": "كهرباء",
        "label_en": "Electricity",
        "main_category": "Utilities",
        "main_cat_ar": "مرافق",
        "is_commercial": False,
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Infrastructure — Transport  (MAINLANDUSE 400000) ─────────────────────
    405000: {
        "label_ar": "نقل ومواصلات",
        "label_en": "Transport & Communications",
        "main_category": "Utilities",
        "main_cat_ar": "مرافق",
        "is_commercial": False,
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Special Use  (MAINLANDUSE 1000000) ────────────────────────────────────
    1001000: {
        "label_ar": "استخدام خاص",
        "label_en": "Special Use",
        "main_category": "Special",
        "main_cat_ar": "خاص",
        "is_commercial": False,
        "capacity_rate": 0,
        "capacity_unit": "",
    },
}

# ---------------------------------------------------------------------------
# DETAILSLANDUSE_MAP — sub-category classification
#
# DETAILSLANDUSE is stored as float64 in the GDB (due to NaN rows).
# Always cast before lookup:  int(float(val))
# 5555 is the universal "unclassified" placeholder across all parent types.
#
# Keys per entry:
#   label_ar        Arabic name (from PARCELNAME field — ground truth)
#   label_en        English translation
#   parent_subtype  SUBTYPE this detail belongs to (int), or None for 5555
#   sub_category    Fine-grained grouping within the parent type
#   capacity_rate   Override capacity rate (0 = inherit from parent SUBTYPE)
#   capacity_unit   Override unit (empty = inherit from parent SUBTYPE)
# ---------------------------------------------------------------------------
DETAILSLANDUSE_MAP = {
    # ── Universal unclassified placeholder ───────────────────────────────────
    5555: {
        "label_ar": "غير محدد",
        "label_en": "Unclassified",
        "parent_subtype": None,
        "sub_category": "Unknown",
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Residential sub-types  (parent: 101000) ───────────────────────────────
    # No Arabic PARCELNAME stored for these — use parent label
    101003: {
        "label_ar": "سكني",
        "label_en": "Residential",
        "parent_subtype": 101000,
        "sub_category": "Residential",
        "capacity_rate": 0,         # inherit 250 m²/unit from parent
        "capacity_unit": "",
    },
    101011: {
        "label_ar": "سكني",
        "label_en": "Residential",
        "parent_subtype": 101000,
        "sub_category": "Residential",
        "capacity_rate": 0,
        "capacity_unit": "",
    },
    101019: {
        "label_ar": "سكني",
        "label_en": "Residential",
        "parent_subtype": 101000,
        "sub_category": "Residential",
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Commercial sub-types  (parent: 201000) ───────────────────────────────
    201011: {
        "label_ar": "محلات تجارية",
        "label_en": "Commercial Shops",
        "parent_subtype": 201000,
        "sub_category": "Commercial",
        "capacity_rate": 0,         # inherit from parent
        "capacity_unit": "",
    },

    # ── Other commercial services sub-types  (parent: 207000) ────────────────
    207042: {
        "label_ar": "خدمات تجارية أخرى",
        "label_en": "Other Commercial Services",
        "parent_subtype": 207000,
        "sub_category": "Commercial",
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Educational sub-types  (parent: 301000) ───────────────────────────────
    301012: {
        "label_ar": "مدرسة ابتدائية بنين",
        "label_en": "Boys Elementary School",
        "parent_subtype": 301000,
        "sub_category": "School",
        "capacity_rate": 4,         # 4 m² per student (elementary)
        "capacity_unit": "m² per student",
    },
    301014: {
        "label_ar": "مدرسة ابتدائية بنات",
        "label_en": "Girls Elementary School",
        "parent_subtype": 301000,
        "sub_category": "School",
        "capacity_rate": 4,
        "capacity_unit": "m² per student",
    },
    301023: {
        "label_ar": "مدرسة متوسطة بنين",
        "label_en": "Boys Middle School",
        "parent_subtype": 301000,
        "sub_category": "School",
        "capacity_rate": 5,         # 5 m² per student (middle school)
        "capacity_unit": "m² per student",
    },
    301024: {
        "label_ar": "مدرسة متوسطة بنات",
        "label_en": "Girls Middle School",
        "parent_subtype": 301000,
        "sub_category": "School",
        "capacity_rate": 5,
        "capacity_unit": "m² per student",
    },

    # ── Health sub-types  (parent: 302000) ────────────────────────────────────
    302033: {
        "label_ar": "مستوصف",
        "label_en": "Polyclinic",
        "parent_subtype": 302000,
        "sub_category": "Clinic",
        "capacity_rate": 20,        # 20 m² per patient
        "capacity_unit": "m² per patient",
    },

    # ── Religious sub-types  (parent: 303000) ─────────────────────────────────
    303006: {
        "label_ar": "مسجد",
        "label_en": "Mosque",
        "parent_subtype": 303000,
        "sub_category": "Mosque",
        "capacity_rate": 1,         # 1 m² per worshipper
        "capacity_unit": "m² per worshipper",
    },
    303010: {
        "label_ar": "سكن إمام",
        "label_en": "Imam Residence",
        "parent_subtype": 303000,
        "sub_category": "Mosque Staff Residence",
        "capacity_rate": 100,       # ~100 m² per residential unit
        "capacity_unit": "m² per unit",
    },
    303011: {
        "label_ar": "سكن مؤذن",
        "label_en": "Muezzin Residence",
        "parent_subtype": 303000,
        "sub_category": "Mosque Staff Residence",
        "capacity_rate": 100,
        "capacity_unit": "m² per unit",
    },
    303012: {
        "label_ar": "سكن الإمام والمؤذن",
        "label_en": "Imam & Muezzin Residence",
        "parent_subtype": 303000,
        "sub_category": "Mosque Staff Residence",
        "capacity_rate": 100,
        "capacity_unit": "m² per unit",
    },
    303013: {
        "label_ar": "مسجد وسكن الإمام والمؤذن",
        "label_en": "Mosque with Imam & Muezzin Residence",
        "parent_subtype": 303000,
        "sub_category": "Mosque",
        "capacity_rate": 1,         # mosque portion dominates
        "capacity_unit": "m² per worshipper",
    },

    # ── Municipal sub-types  (parent: 304000) ─────────────────────────────────
    304006: {
        "label_ar": "دورة مياه",
        "label_en": "Public Restroom",
        "parent_subtype": 304000,
        "sub_category": "Sanitation",
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Recreational sub-types  (parent: 306000) ──────────────────────────────
    306011: {
        "label_ar": "حديقة",
        "label_en": "Garden / Park",
        "parent_subtype": 306000,
        "sub_category": "Park",
        "capacity_rate": 10,        # 10 m² per visitor
        "capacity_unit": "m² per visitor",
    },

    # ── Electricity sub-types  (parent: 401000) ───────────────────────────────
    401002: {
        "label_ar": "محطة كهرباء",
        "label_en": "Power Station",
        "parent_subtype": 401000,
        "sub_category": "Electricity",
        "capacity_rate": 0,
        "capacity_unit": "",
    },

    # ── Transport sub-types  (parent: 405000) ─────────────────────────────────
    405032: {
        "label_ar": "جزيرة",
        "label_en": "Traffic Island",
        "parent_subtype": 405000,
        "sub_category": "Road Infrastructure",
        "capacity_rate": 0,
        "capacity_unit": "",
    },
    405052: {
        "label_ar": "ممر للمشاة",
        "label_en": "Pedestrian Path",
        "parent_subtype": 405000,
        "sub_category": "Pedestrian",
        "capacity_rate": 0,
        "capacity_unit": "",
    },
    405053: {
        "label_ar": "ممر مشاة",
        "label_en": "Pedestrian Walkway",
        "parent_subtype": 405000,
        "sub_category": "Pedestrian",
        "capacity_rate": 0,
        "capacity_unit": "",
    },
    405055: {
        "label_ar": "مواقف سيارات",
        "label_en": "Parking",
        "parent_subtype": 405000,
        "sub_category": "Parking",
        "capacity_rate": 25,        # ~25 m² per parking space
        "capacity_unit": "m² per space",
    },

    # ── Special use sub-types  (parent: 1001000) ──────────────────────────────
    1001001: {
        "label_ar": "استخدام خاص",
        "label_en": "Special Use",
        "parent_subtype": 1001000,
        "sub_category": "Special",
        "capacity_rate": 0,
        "capacity_unit": "",
    },
}
