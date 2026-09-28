import re

# Door tags in this project family are usually room/door numbers. This remains
# intentionally conservative; geometry, not the regex, creates doors.
TAG_PATTERN = re.compile(r'^\d{3,5}[A-Z]?$')
RENDER_DPI = 150
OUT_DIR = 'out'

# ---------------- Physical geometry (feet) ----------------
# Geometry thresholds are expressed in real-world feet and converted to PDF
# points using each floor-plan view's drawing scale. This is the key change
# from v4: no page numbers and no 1/4"-scale-specific door sizes.
ARC_SEG_MIN_FT = 0.025
ARC_SEG_MAX_FT = 0.667
ARC_COMPONENT_MIN_SEGMENTS = 6
ARC_COMPONENT_MAX_SEGMENTS = 25
DOOR_LEAF_MIN_FT = 1.89
DOOR_LEAF_MAX_FT = 4.78
ARC_SPAN_MIN_DEG = 78.0
ARC_SPAN_MAX_DEG = 100.0
ARC_RMS_MAX_FT = 0.036
ENDPOINT_SNAP_FT = 0.010
LEAF_CENTER_TOL_FT = 0.222
LEAF_ENDPOINT_TOL_FT = 0.222
LEAF_RATIO_MIN = 0.72
LEAF_RATIO_MAX = 1.30

# CAD line weights are paper-space properties, so they stay in PDF points.
ARC_STROKE_MAX_PT = 0.42
LEAF_STROKE_MIN_PT = 0.55
LEAF_STROKE_MAX_PT = 0.90

# Door-tag matching. Spatial radius is physical, while badge/text geometry is
# paper-space and therefore stays in PDF points.
TAG_RADIUS_FT = 4.0
TAG_DEDUPE_PT = 1.0

# Intra-sheet duplicate geometry.
DOOR_CENTER_DEDUPE_FT = 0.278
DOOR_RADIUS_DEDUPE_FT = 0.222

# Fallback leaf recovery (physical dimensions).
TAG_AXIS_LEAF_MAX_DIST_FT = 1.78
TAG_DIAG_LEAF_MAX_DIST_FT = 2.89
LEAF_DUP_MID_FT = 0.194
LEAF_DUP_LEN_FT = 0.167
LEAF_DUP_ANGLE_DEG = 4.0
DIAG_ANGLE_MARGIN_DEG = 12.0
DOUBLE_PAIR_MAX_MID_DIST_FT = 5.28
DOUBLE_PAIR_MAX_ENDPOINT_GAP_FT = 2.11
FALLBACK_DOOR_DEDUPE_FT = 1.0

# Cross-sheet reconciliation.
REG_MIN_SHARED_TAGS = 2
REG_MAX_TAG_RESIDUAL_FT = 1.25
CROSS_SHEET_MATCH_FT = 1.4
CROSS_SHEET_RADIUS_RATIO_TOL = 0.35
REG_SCALE_RATIO_TOL = 0.18

# Visualization.
MARKER_RADIUS_PX = 9

# Sheet classification. We process floor plans automatically rather than fixed
# page numbers. Unknown sheets are skipped unless --include-unknown is used.
FLOOR_POSITIVE = (
    'FLOOR PLAN', 'ENLARGED PLAN', 'OVERALL PLAN', 'LEVEL PLAN',
)
FLOOR_NEGATIVE = (
    'REFLECTED CEILING', 'RCP', 'ROOF PLAN', 'FINISH PLAN', 'DEMOLITION PLAN',
    'ELEVATION', 'SECTION', 'DETAIL', 'DOOR SCHEDULE', 'WINDOW SCHEDULE',
)

# Double-leaf recovery is reliable on detailed views; at lower scales it is
# retained as a review candidate rather than counted automatically.
LOW_DETAIL_DOUBLE_MIN_PPF = 13.5
