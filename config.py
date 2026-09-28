# global knobs for the floorplan experiment. tweak these when a new
# bid set comes in with a different scale or tag style

import re

# door tags on these sheets look like 1400, 1422, 1403A. keynotes are 6
# digits and grid bubbles are 1-2 digits so they naturally fall out
TAG_PATTERN = re.compile(r"^\d{3,4}[A-Z]?$")

# render dpi for the annotated screenshots, 150 is plenty and keeps
# the pngs small enough to share on discord
RENDER_DPI = 150

# door swing arc sizes in pdf points. at 1/4" scale a 3ft door swing is
# ~54pt, at 1/8" its ~27pt, so this window covers both plus pairs
ARC_MIN_PT = 15
ARC_MAX_PT = 110

# a quarter circle swing is about as wide as tall, furniture curves
# and site contours usually are not
ARC_RATIO_MIN = 0.7
ARC_RATIO_MAX = 1.4

# wall gap window. a door opening breaks the wall line by roughly the
# door width, so hairline cracks and corridor mouths get ignored
GAP_MIN_PT = 14
GAP_MAX_PT = 90

# how far a tag can sit from its swing arc or gap and still count as
# the same door, architects put the badge just outside the swing
MATCH_RADIUS_PT = 90

# short ticks and furniture lines just add noise to the wall graph
WALL_MIN_LEN_PT = 60

OUT_DIR = "out"