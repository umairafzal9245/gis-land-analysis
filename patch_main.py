import re

with open("backend/main.py", "r") as f:
    content = f.read()

# I want to add validation to analyze_bbox
validation_logic = """
    # Validate Riyadh coordinate order (Fix for Issue 1)
    if not (24 < req.min_lat < 26 and 46 < req.min_lon < 48):
        # Coordinates might be swapped, let's swap them back internally or just raise an error
        # Actually the prompt says "If you see values outside these ranges, your coordinates are swapped."
        pass 
        # Hmm we should probably swap them back or raise an error. Let's swap them back.
        # But wait! If max_lat is also swapped etc it's complicated. Best to swap lat and lon.
        # Actually if they are outside this range, we assume lat was sent as lon and lon as lat.
        req.min_lat, req.min_lon = req.min_lon, req.min_lat
        req.max_lat, req.max_lon = req.max_lon, req.max_lat
        
"""

# Let's see how api_analyze_bbox looks like
content = content.replace(
    'def api_analyze_bbox(req: BBoxRequest):\n    try:',
    'def api_analyze_bbox(req: BBoxRequest):\n    try:\n        if not (24 < req.min_lat < 26 and 46 < req.min_lon < 48):\n            req.min_lat, req.min_lon = req.min_lon, req.min_lat\n            req.max_lat, req.max_lon = req.max_lon, req.max_lat'
)

with open("backend/main.py", "w") as f:
    f.write(content)
