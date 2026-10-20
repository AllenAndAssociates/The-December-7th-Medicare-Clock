"""Edit decision list for the main video (Scenes 6-18).

Builds timeline.json: the cut list, word-level cue times on the output
timeline, speaker blocking keyframes, music automation and SFX hits.
Everything downstream (graphics, compositor, mixer) reads that file.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
WORDS = json.load(open(os.path.join(ROOT, "transcripts", "words.json")))

C = {
    "partb": "Applying_for_Medicare_Part_B_20261020200651.mp4",
    "underwrite": "Applying_for_Medicare_Supplement…_1080p_20261020195722.mp4",
    "partd": "Changing_Medicare_Part_D_plan_20261020200242.mp4",
    "nuance": "Choosing_Medicare_plan_before_De…_20261020202455.mp4",
    "leaving": "Leaving_Medicare_Advantage_plan_1080p_20261020195931.mp4",
    "terminated": "Medicare_Advantage_plan_terminat…_1080p_20261020200744.mp4",
    "switchma": "Medicare_enrollment_deadline_Dec…_1080p_20261020200459.mp4",
    "summary": "Medicare_plan_enrollment_deadline_1080p_20261020202547.mp4",
    "nofall": "Medicare_supplement_open_enrollm…_1080p_20261020200554.mp4",
    "lockin": "Reviewing_Medicare_Part_D_plans_20261020200401.mp4",
    "flip": "Spoken_audio_about_Medigap_policies_20261020200114.mp4",
}

# (scene, kind, source, in, out). "clip" = Arric on camera, "vo" = cloned-voice
# pickup played over a full-frame graphic cutaway.
CUTS = [
    (6, "clip", C["partd"], 0.70, 9.40),
    (7, "clip", C["lockin"], 0.45, 9.52),
    (7, "vo", "vo/vo7.mp3", 0.00, 3.62),
    (8, "clip", C["switchma"], 0.30, 8.38),   # cut before the misspoken "January seventh"
    (8, "vo", "vo/vo8.mp3", 0.00, 2.90),
    (9, "clip", C["leaving"], 0.00, 9.84),
    (10, "vo", "vo/vo10.mp3", 0.00, 4.50),
    (10, "clip", C["underwrite"], 1.38, 9.90),  # skip the doubled "in most states"
    (11, "clip", C["flip"], 0.25, 9.10),
    (12, "clip", C["nofall"], 0.00, 9.95),
    (13, "clip", C["partb"], 0.00, 10.00),
    (14, "clip", C["terminated"], 0.00, 9.92),
    (15, "clip", C["nuance"], 0.10, 9.90),
    (16, "clip", C["summary"], 0.35, 9.70),
    (17, "vo", "vo/vo17.mp3", 0.00, 16.30),
    (18, "vo", "vo/vo18.mp3", 0.00, 8.39),
]
LEAD = {17: 0.4}          # breathing room before a scene starts talking
TAIL = 3.2                # sign-off hold so the end card can be read


def build():
    t = 0.0
    pieces, scenes = [], {}
    for scene, kind, src, a, b in CUTS:
        t += LEAD.get(scene, 0.0) if scene not in scenes else 0.0
        scenes.setdefault(scene, t - LEAD.get(scene, 0.0))
        pieces.append({"scene": scene, "kind": kind, "src": src, "in": a, "out": b,
                       "start": round(t, 3), "end": round(t + b - a, 3)})
        t += b - a
    total = round(t + TAIL, 3)
    return pieces, scenes, total


PIECES, SCENE_START, TOTAL = build()


def words(scene):
    out = []
    for p in PIECES:
        if p["scene"] != scene:
            continue
        for w in WORDS[p["src"]]:
            if w["s"] >= p["in"] - 0.05 and w["e"] <= p["out"] + 0.05:
                out.append((w["w"].lower().strip(",.?!"), p["start"] + w["s"] - p["in"]))
    return out


def at(scene, word, n=1, off=0.0):
    """Output time of the n-th occurrence of `word` in `scene`."""
    k = 0
    for w, s in words(scene):
        if w.startswith(word):
            k += 1
            if k == n:
                return round(s + off, 3)
    raise KeyError((scene, word, n))


def piece(scene, kind):
    return next(p for p in PIECES if p["scene"] == scene and p["kind"] == kind)


S = SCENE_START
CUE = {f"s{k}": round(v, 3) for k, v in S.items()}
CUE["end"] = TOTAL
CUE.update({
    # Scene 6
    "s6_three": at(6, "three"), "s6_first": at(6, "first"),
    # Scene 7
    "s7_form": at(7, "formularies"), "s7_pharm": at(7, "pharmacy"), "s7_copay": at(7, "copays"),
    "s7_vo": piece(7, "vo")["start"], "s7_locked": at(7, "locked"), "s7_year": at(7, "calendar"),
    # Scene 8
    "s8_arrow1": at(8, "one"), "s8_arrow2": at(8, "moving"),
    "s8_vo": piece(8, "vo")["start"], "s8_dec": at(8, "december"),
    # Scene 9
    "s9_step1": at(9, "leaving"), "s9_step2": at(9, "original"), "s9_step3": at(9, "standalone"),
    # Scene 10
    "s10_apply": at(10, "apply"), "s10_back": piece(10, "clip")["start"],
    "s10_check1": at(10, "approved"), "s10_check2": at(10, "add"),
    # Scene 11
    "s11_flip": at(11, "flip"), "s11_first": at(11, "first"),
    # Scene 12
    "s12_no": at(12, "no"), "s12_year": at(12, "year-round"), "s12_health": at(12, "health"),
    # Scene 13
    "s13_bday": at(13, "birthday"), "s13_work": at(13, "work"), "s13_not": at(13, "not"),
    # Scene 14
    "s14_letter": at(14, "letter"), "s14_term": at(14, "terminated"), "s14_tech": at(14, "replacement"),
    # Scene 15
    "s15_special": at(15, "special"), "s15_still": at(15, "recommend"), "s15_jan": at(15, "january"),
    # Scene 16
    "s16_partd": at(16, "part"), "s16_clock": at(16, "different"),
    # Scene 17
    "s17_partd": at(17, "part"), "s17_ma": at(17, "advantage"), "s17_gap": at(17, "medigap"),
    "s17_call": at(17, "call"), "s17_visit": at(17, "visit"),
    # Scene 18
    "s18_sub": at(18, "subscribe"), "s18_share": at(18, "share"),
})

# ---- speaker blocking: keyframes of (time, x as fraction of width, scale %) ----
# Punch-ins sit a little further out than the 25% / 75% thirds so the wider
# close-up framing doesn't cover the graphic cards.
# Each entry holds until the next; "ease" keyframes interpolate from the previous one.
F = 1 / 30
BLOCK = [
    {"t": S[6], "x": 0.50, "s": 100},
    {"t": CUE["s6_three"], "x": 0.50, "s": 100},
    {"t": CUE["s6_three"] + 12 * F, "x": 0.25, "s": 100, "ease": True},
    {"t": S[7], "x": 0.23, "s": 118},
    {"t": S[8], "x": 0.25, "s": 100},
    {"t": S[9], "x": 0.25, "s": 100},
    {"t": CUE["s10_back"], "x": 0.225, "s": 120},
    {"t": S[11], "x": 0.25, "s": 100},
    {"t": CUE["s11_flip"], "x": 0.25, "s": 100},
    {"t": CUE["s11_flip"] + 15 * F, "x": 0.75, "s": 100, "ease": True},
    {"t": S[12], "x": 0.775, "s": 115},
    {"t": S[13], "x": 0.75, "s": 100},
    {"t": S[14], "x": 0.75, "s": 100},
    {"t": S[15], "x": 0.785, "s": 118},
    {"t": S[16], "x": 0.785, "s": 118},
    {"t": S[16] + 15 * F, "x": 0.20, "s": 92, "ease": True},
]
# Arric is hidden while a pickup line plays over a full-frame graphic.
HIDDEN = [[p["start"], p["end"]] for p in PIECES if p["kind"] == "vo" and p["scene"] < 17]
HIDDEN.append([S[17], TOTAL])  # contact card owns the frame from Scene 17 on

# ---- music: two beds, gain envelope in dB (keyframes, linear ramps) ----
B_START = CUE["s11_first"] - 0.15
MUSIC = [
    {"src": "music/a.mp3", "at": S[6], "from": 0.0, "until": CUE["s11_flip"] - 0.6,
     "env": [[S[6], -60], [S[6] + 0.25, -26], [S[10] - 0.08, -26], [S[10], -90],
             [S[10] + 2.6, -90], [S[10] + 3.4, -28], [S[11] - 0.15, -28], [S[11], -90]]},
    # Bed B is offset so its natural final chord lands on the last frame.
    {"src": "music/b.mp3", "at": B_START, "from": None, "until": TOTAL,
     "env": [[B_START, -60], [B_START + 0.2, -26], [S[17] - 0.3, -26], [S[17] + 1.2, -22],
             [S[18], -23], [TOTAL - 4, -23], [TOTAL, -30]]},
]

# ---- SFX hits: (time, name, gain dB, pitch semitones) ----
SFX = [
    (S[6] + 0.15, "whoosh", -6, 0),
    (CUE["s6_three"] + 0.05, "whoosh", -4, 0),
    (CUE["s6_three"] + 0.55, "tick", -4, 0), (CUE["s6_three"] + 0.72, "tick", -4, 1),
    (CUE["s6_three"] + 0.89, "tick", -4, 2),
    (CUE["s6_first"], "cardpop", -4, 0),
    (CUE["s7_form"], "pop", -6, 0), (CUE["s7_pharm"], "pop", -6, 2), (CUE["s7_copay"], "pop", -6, 4),
    (CUE["s7_vo"] + 0.05, "whoosh", -6, -2),
    (CUE["s7_vo"] + 0.35, "counter", -8, 0),
    (CUE["s7_locked"], "padlock", -3, 0),
    (S[8], "snap", -4, 0),
    (CUE["s8_arrow1"], "swish", -6, 0), (CUE["s8_arrow2"], "swish", -6, 2),
    (CUE["s8_vo"] + 0.05, "whoosh", -6, -2),
    (CUE["s8_dec"], "stamp", -2, 0),
    (S[9], "snap", -4, 0),
    (CUE["s9_step1"], "pop", -5, -4), (CUE["s9_step2"], "pop", -5, 0), (CUE["s9_step3"], "pop", -5, 4),
    (CUE["s10_apply"] - 0.05, "chime", -6, 0), (CUE["s10_apply"] + 0.15, "marker", -6, 0),
    (CUE["s10_check1"], "ding", -6, 0), (CUE["s10_check2"], "ding", -6, 2),
    (CUE["s11_flip"] - 0.05, "flip", -3, 0),
    (CUE["s11_first"], "pop", -5, 3),
    (CUE["s12_no"], "buzz", -10, 0),
    (CUE["s12_year"] - 0.3, "flutter", -8, 0),
    (CUE["s12_health"], "pop", -6, 0),
    (S[13], "snap", -4, 0),
    (CUE["s13_bday"], "marimba", -6, 0), (CUE["s13_work"], "marimba", -6, 3),
    (CUE["s13_not"], "swipe", -5, 0),
    (S[14], "snap", -4, 0),
    (CUE["s14_letter"], "envelope", -6, 0),
    (CUE["s14_tech"] + 0.2, "reassure", -6, 0),
    (CUE["s15_special"], "stretch", -8, 0),
    (CUE["s15_still"] + 0.1, "bell", -7, 0),
    (S[16] + 0.05, "shuffle", -5, 0),
    (CUE["s16_partd"], "ding", -9, 0), (CUE["s16_partd"] + 0.25, "ding", -9, 3),
    (CUE["s16_clock"] + 0.2, "clock", -8, 0),
    (S[17] + 0.1, "whoosh", -6, 0),
    (CUE["s17_partd"], "pop", -6, 0), (CUE["s17_ma"], "pop", -6, 2), (CUE["s17_gap"], "pop", -6, 4),
    (CUE["s17_call"] + 0.35, "keys", -9, 0),
    (CUE["s17_visit"] + 0.1, "click", -6, 0),
    (CUE["s18_sub"], "subbell", -6, 0),
]

if __name__ == "__main__":
    tl = {"fps": 30, "width": 1920, "height": 1080, "total": TOTAL,
          "pieces": PIECES, "cues": CUE, "block": BLOCK, "hidden": HIDDEN,
          "music": MUSIC, "sfx": [{"t": round(t, 3), "name": n, "db": g, "pitch": p} for t, n, g, p in SFX]}
    json.dump(tl, open(os.path.join(ROOT, "timeline.json"), "w"), indent=1, ensure_ascii=False)
    for k, v in sorted(CUE.items(), key=lambda kv: kv[1]):
        print(f"{v:8.2f}  {k}")
