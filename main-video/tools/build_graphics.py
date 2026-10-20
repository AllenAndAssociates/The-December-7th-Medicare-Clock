"""Fill the graphics template with cue times from timeline.json."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tl = json.load(open(os.path.join(ROOT, "timeline.json")))
src = open(os.path.join(ROOT, "tools", "graphics.template.html")).read()
phone = "".join(f"<span>{c}</span>" for c in "800-324-9986")
html = (src.replace("__CUES__", json.dumps(tl["cues"]))
           .replace("__TOTAL__", str(tl["total"]))
           .replace("__PHONE__", phone))
open(os.path.join(ROOT, "graphics", "index.html"), "w").write(html)
print("graphics/index.html written,", tl["total"], "s")
