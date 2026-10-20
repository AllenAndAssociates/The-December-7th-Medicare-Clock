# Main video: Parts 2–4 (Scenes 6–18)

Output: `../Medicare_Clock_Main_Video.mp4`, 1920×1080, 30 fps, 2:21, about -14 LUFS.
Rebuild with `./build.sh` (needs ffmpeg, Python 3 with numpy and Pillow, and Node for HyperFrames).

## Clip → scene map

| Scene | Clip | Notes |
|---|---|---|
| 6 | Changing_Medicare_Part_D_plan | |
| 7 | Reviewing_Medicare_Part_D_plans | Clip stops at "…by December seventh". The pickup line "you are locked into that plan for the entire next calendar year" plays over the calendar/padlock graphic. |
| 8 | Medicare_enrollment_deadline_Dec… | The clip says "January **seventh** is your deadline", so it's cut after "start". The pickup "January first. December seventh is your deadline" plays over the Dec 7 → Jan 1 graphic. |
| 9 | Leaving_Medicare_Advantage_plan | |
| 10 | Applying_for_Medicare_Supplement… | The opening line isn't in the clip, so the pickup "Here is a critical insider tip…" plays over the Medigap zoom. The doubled "in most states" is trimmed. |
| 11 | Spoken_audio_about_Medigap_policies | |
| 12 | Medicare_supplement_open_enrollm… | |
| 13 | Applying_for_Medicare_Part_B | |
| 14 | Medicare_Advantage_plan_terminat… | |
| 15 | Choosing_Medicare_plan_before_De… | The clip leaves out "through the end of February" and "before the end of December". The on-screen timeline and Best Practice badge show both. |
| 16 | Medicare_plan_enrollment_deadline | |
| 17–18 | No footage | Arric's cloned ElevenLabs voice plays over the contact card, which shows a keyed portrait. |

## Layout
- `tools/edl.py`: cut list, word-timed cues (from ElevenLabs Scribe transcripts in `transcripts/`), speaker blocking, music automation, and SFX hits. Writes `timeline.json`.
- `tools/graphics.template.html` → `graphics/index.html`: HyperFrames/GSAP graphics layer on the `#F4F4F0` canvas.
- `tools/composite.py` + `tools/keyer.py`: green-screen key, bottom-anchored, with the left/center/right slides and 100/115/118/120% punch-ins.
- `tools/mix.py`: dialogue leveled per cut, two ElevenLabs Music beds (urgent pizzicato/marimba for Part 2, relaxed groove for Parts 3–4) with hard stops at Scenes 10 and 11, and ElevenLabs SFX.
- `audio/`: pickup lines (`vo/`), music beds, SFX. `audio/sfx/prompts.tsv` lists the prompts used to generate each sound.
