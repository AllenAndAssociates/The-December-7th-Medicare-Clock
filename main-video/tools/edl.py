"""Edit decision list for the main video (Scenes 6-18).

Builds timeline.json: the cut list, word-level cue times on the output
timeline, speaker blocking keyframes, music automation and SFX hits.
Everything downstream (graphics, compositor, mixer) reads that file.

Every on-camera cut plays Arric's speech-to-speech converted audio
(audio/sts/), so the clips and the cloned-voice pickups (audio/vo/) are the
same voice.
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
HEAD, TAIL_PAD = 0.08, 0.12   # keep this much air around the first/last word of a cut


def clip(key, a=None, b=None):
    """On-camera cut; a/b default to the first/last word of the clip, padded."""
    ws = WORDS[C[key]]
    a = max(0.0, ws[0]["s"] - HEAD) if a is None else a
    b = min(10.0, ws[-1]["e"] + TAIL_PAD) if b is None else b
    return ("clip", key, a, b)


def vo(name):
    ws = WORDS[f"vo/{name}.mp3"]
    return ("vo", name, 0.0, round(ws[-1]["e"] + 0.15, 3))


# (scene, cut). "clip" = Arric on camera, "vo" = cloned-voice pickup played over
# a full-frame graphic cutaway (lines the clips are missing or misspeak).
CUTS = [
    (6, clip("partd")),
    (7, clip("lockin")),
    (7, vo("vo7")),                        # "you are locked into that plan..."
    (8, clip("switchma", b=8.40)),         # stop before the misspoken "January seventh"
    (8, vo("vo8")),
    (9, clip("leaving")),
    (10, vo("vo10")),                      # "Here is a critical insider tip..."
    (10, clip("underwrite", 1.38, 6.15)),  # skip the doubled "in most states"; stop at "supplement"
    (10, vo("vo10b")),                     # "before you drop your Advantage plan..."
    (11, clip("flip")),
    (12, clip("nofall")),
    (13, clip("partb")),
    (14, clip("terminated")),
    (15, clip("nuance", b=2.50)),          # "...Medicare gives you a"
    (15, vo("vo15a")),                     # "Special Enrollment Period that lasts through..."
    (15, clip("nuance", 3.72, 6.62)),      # "Still, I recommend choosing your new plan"
    (15, vo("vo15b")),                     # "before the end of December, so your coverage..."
    (16, clip("summary", b=5.46)),         # "...switching a Part D drug plan,"
    (16, vo("vo16")),                      # "or a Medicare Advantage plan,"
    (16, clip("summary", 5.70)),           # "December seventh is your hard deadline..."
    (17, vo("vo17")),
    (18, vo("vo18")),
]
LEAD = {17: 0.3}          # breathing room before a scene starts talking
TAIL = 3.0                # sign-off hold so the end card can be read


def build():
    t = 0.0
    pieces, scenes = [], {}
    for scene, (kind, key, a, b) in CUTS:
        if scene not in scenes:
            t += LEAD.get(scene, 0.0)
            scenes[scene] = t - LEAD.get(scene, 0.0)
        if kind == "clip":
            src, audio = C[key], f"sts/{key}.mp3"
        else:
            src = audio = f"vo/{key}.mp3"
        pieces.append({"scene": scene, "kind": kind, "src": src, "audio": audio, "in": a, "out": b,
                       "start": round(t, 3), "end": round(t + b - a, 3)})
        t += b - a
    return pieces, scenes, round(t + TAIL, 3)


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


def vo_piece(name):
    return next(p for p in PIECES if p["src"] == f"vo/{name}.mp3")


def clip_pieces(scene):
    return [p for p in PIECES if p["scene"] == scene and p["kind"] == "clip"]


S = SCENE_START
CUE = {f"s{k}": round(v, 3) for k, v in S.items()}
CUE["end"] = TOTAL
for name in ["vo7", "vo8", "vo10", "vo10b", "vo15a", "vo15b", "vo16"]:
    CUE[name] = vo_piece(name)["start"]
    CUE[name + "_end"] = vo_piece(name)["end"]
CUE.update({
    "s6_three": at(6, "three"), "s6_first": at(6, "first"),
    "s7_form": at(7, "formularies"), "s7_pharm": at(7, "pharmacy"), "s7_copay": at(7, "copays"),
    "s7_locked": at(7, "locked"),
    "s8_arrow1": at(8, "one"), "s8_arrow2": at(8, "moving"), "s8_dec": at(8, "december"),
    "s9_step1": at(9, "leaving"), "s9_step2": at(9, "original"), "s9_step3": at(9, "standalone"),
    "s10_apply": at(10, "apply"), "s10_back": clip_pieces(10)[0]["start"],
    "s10_check1": at(10, "approved"), "s10_check2": at(10, "add"),
    "s11_flip": at(11, "flip"), "s11_first": at(11, "first"),
    "s12_no": at(12, "no"), "s12_year": at(12, "year-round"), "s12_health": at(12, "health"),
    "s13_bday": at(13, "birthday"), "s13_work": at(13, "work"), "s13_not": at(13, "not"),
    "s14_letter": at(14, "letter"), "s14_term": at(14, "terminated"), "s14_tech": at(14, "replacement"),
    "s15_feb": at(15, "february"), "s15_still": clip_pieces(15)[1]["start"], "s15_dec": at(15, "december"),
    "s16_partd": at(16, "part"), "s16_ma": at(16, "advantage"), "s16_hard": at(16, "hard"),
    "s16_back": clip_pieces(16)[1]["start"], "s16_clock": at(16, "different"),
    "s17_partd": at(17, "part"), "s17_ma": at(17, "advantage"), "s17_gap": at(17, "medigap"),
    "s17_call": at(17, "call"), "s17_visit": at(17, "visit"),
    "s18_sub": at(18, "subscribe"), "s18_share": at(18, "share"),
})
CUE["s7_lock"] = round(CUE["vo7"] + 1.45, 3)  # padlock lands once the red bar has crossed the year

# ---- speaker blocking: keyframes of (time, x as fraction of width, scale %) ----
# Each entry holds until the next; an "ease" keyframe moves from the previous one.
# Punch-ins sit further out than the 25% / 75% thirds so the wider close-up
# framing never covers the graphic cards.
F = 1 / 30
BLOCK = [
    {"t": S[6], "x": 0.50, "s": 100},
    {"t": CUE["s6_three"], "x": 0.50, "s": 100},
    {"t": CUE["s6_three"] + 12 * F, "x": 0.25, "s": 100, "ease": "inout"},
    {"t": S[7], "x": 0.22, "s": 118},
    {"t": S[8], "x": 0.25, "s": 100},
    {"t": S[9], "x": 0.25, "s": 100},
    {"t": CUE["s10_back"], "x": 0.215, "s": 120},
    {"t": S[11], "x": 0.25, "s": 100},
    {"t": CUE["s11_flip"], "x": 0.25, "s": 100},
    {"t": CUE["s11_flip"] + 10 * F, "x": 0.75, "s": 100, "ease": "inout"},
    {"t": S[12], "x": 0.80, "s": 115},
    {"t": S[13], "x": 0.75, "s": 100},
    {"t": S[14], "x": 0.75, "s": 100},
    {"t": S[15], "x": 0.84, "s": 118},
    {"t": S[16], "x": 0.84, "s": 118},
    {"t": S[16] + 15 * F, "x": 0.20, "s": 92, "ease": "inout"},
]
# Arric is hidden (hard cut) while a pickup plays over a full-frame graphic,
# and from Scene 17 on the contact card owns the frame.
HIDDEN = [[p["start"], p["end"]] for p in PIECES if p["kind"] == "vo" and p["scene"] < 17]
HIDDEN.append([S[17], TOTAL])

# ---- music: two beds, gain envelope in dB (keyframes, linear ramps) ----
B_START = CUE["s11_first"] - 0.15
MUSIC = [
    {"src": "music/a.mp3", "at": S[6], "from": 0.0, "until": S[11],
     "env": [[S[6], -60], [S[6] + 0.25, -26], [S[10] - 0.08, -26], [S[10], -90],
             [S[10] + 2.0, -90], [S[10] + 2.8, -28], [S[11] - 0.15, -28], [S[11], -90]]},
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
    (CUE["vo7"], "whoosh", -6, -2),
    (CUE["vo7"] + 0.2, "counter", -8, 0),
    (CUE["s7_lock"], "padlock", -3, 0),
    (S[8], "snap", -4, 0),
    (CUE["s8_arrow1"], "swish", -6, 0), (CUE["s8_arrow2"], "swish", -6, 2),
    (CUE["vo8"], "whoosh", -6, -2),
    (CUE["s8_dec"], "stamp", -2, 0),
    (S[9], "snap", -4, 0),
    (CUE["s9_step1"], "pop", -5, -4), (CUE["s9_step2"], "pop", -5, 0), (CUE["s9_step3"], "pop", -5, 4),
    (CUE["s10_apply"] - 0.05, "chime", -6, 0), (CUE["s10_apply"] + 0.15, "marker", -6, 0),
    (CUE["s10_check1"], "ding", -6, 0),
    (CUE["vo10b"], "whoosh", -7, -2), (CUE["s10_check2"], "ding", -6, 2),
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
    (CUE["vo15a"], "whoosh", -7, -2), (CUE["vo15a"] + 0.4, "stretch", -8, 0),
    (CUE["vo15b"], "whoosh", -7, -2), (CUE["s15_dec"], "bell", -7, 0),
    (S[16] + 0.05, "shuffle", -5, 0),
    (CUE["s16_partd"], "ding", -9, 0), (CUE["s16_ma"], "ding", -9, 3),
    (CUE["s16_hard"], "stamp", -8, 0),
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
