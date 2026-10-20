# Main video: Parts 2–4 (Scenes 6–18)

Output: `../Medicare_Clock_Main_Video.mp4`, 1920×1080, 30 fps, 2:22, -14 LUFS.
Rebuild with `./build.sh` (needs ffmpeg, Python 3 with numpy and Pillow, and Node for HyperFrames).

## Voice
All on-camera audio is Arric's own clip speech converted to his ElevenLabs voice with speech-to-speech (`audio/sts/`, timing preserved within ~20 ms so lip sync holds). Lines the clips are missing or misspeak are cloned-voice pickups (`audio/vo/`) played over full-frame cards. Every voice piece is EQ-matched to one shared spectrum, leveled, de-clicked, and compressed as a single bus; the master is normalized to -14 LUFS.

## Clip → scene map

| Scene | On camera | Pickup over a full-frame card |
|---|---|---|
| 6 | Changing_Medicare_Part_D_plan | |
| 7 | Reviewing_Medicare_Part_D_plans | "you are locked into that plan for the entire next calendar year" |
| 8 | Medicare_enrollment_deadline_Dec… (cut before "January seventh") | "January first, December seventh is your deadline" |
| 9 | Leaving_Medicare_Advantage_plan | |
| 10 | Applying_for_Medicare_Supplement… (doubled "in most states" trimmed) | "Here is a critical insider tip…" and "before you drop your Advantage plan, and add Part D by December seventh" |
| 11–14 | Spoken_audio_about_Medigap_policies, Medicare_supplement_open_enrollm…, Applying_for_Medicare_Part_B, Medicare_Advantage_plan_terminat… | |
| 15 | Choosing_Medicare_plan_before_De… (two cuts) | "Special Enrollment Period that lasts through the end of February" and "before the end of December, so your coverage starts smoothly on January first" |
| 16 | Medicare_plan_enrollment_deadline (two cuts) | "or a Medicare Advantage plan" (the board slides to center) |
| 17–18 | No footage: contact card with silent, smiling footage of Arric looping live in the portrait circle | Call to action and sign-off |

## Layout
- `tools/edl.py`: cut list, word-timed cues (from ElevenLabs Scribe transcripts in `transcripts/`), speaker blocking, music automation, and SFX hits. Writes `timeline.json`.
- `tools/graphics.template.html` → `graphics/index.html`: HyperFrames/GSAP graphics layer on the `#F4F4F0` canvas.
- `tools/composite.py` + `tools/keyer.py`: green-screen key, bottom-anchored, with the left/center/right slides and 100/115/118/120% punch-ins.
- `tools/mix.py`: dialogue leveled per cut, two ElevenLabs Music beds (urgent pizzicato/marimba for Part 2, relaxed groove for Parts 3–4) with hard stops at Scenes 10 and 11, and ElevenLabs SFX.
- `audio/`: pickup lines (`vo/`), music beds, SFX. `audio/sfx/prompts.tsv` lists the prompts used to generate each sound.
