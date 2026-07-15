# Frontend Design Notes

## Design Goals

The redesigned frontend is intended to feel like a serious decision-support review dashboard for chest X-ray report generation, structured finding extraction, and clinical review preparation.

## Inspiration

Reference sites were used only for directional inspiration:

- Decision-support workflow tone and prioritization cues from radiology review tooling.
- Chest X-ray AI and triage framing from Qure.ai.
- Restrained medical imaging workspace cues from OHIF.
- Enterprise imaging and healthcare software tone from GE HealthCare.
- Component polish patterns inspired by shadcn/ui, Radix UI, and Lucide, without copying layouts or installing a UI system.

## Visual Palette

- Background: light blue-gray off-white.
- Primary: deep clinical navy.
- Secondary: muted cyan/teal.
- Risk: controlled rose.
- Warning: amber.
- Success: clinical green.
- Neutral: slate gray.

## What Changed

- Header now presents the project title, clinical subtitle, and status badges.
- Upload flow now resembles a clinical image intake workspace.
- Analysis control now shows a four-step visual workflow and real-run timing note.
- Results now use a top overview row for case summary, decision support, and runtime metadata.
- Generated report sections use restrained clinical report styling.
- Structured findings table has clearer state badges, probability bars, and active-row emphasis.
- Export panel is calmer and artifact-oriented.

## Notes

The frontend architecture and API behavior were preserved. Backend logic, endpoint names, and response expectations were not changed.
