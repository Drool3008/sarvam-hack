# Build note — two functionalities

`README.md` is the product specification for the whole Family Health Agent.
This build implements **two** of its functionalities end to end on Sarvam AI,
and deliberately leaves the rest out rather than stubbing it.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Drool3008/sarvam-hack)

## 1. The person talks to the agent — `POST /agent/talk`

A household member sends a voice note (or types), and the agent answers them in
their own language, out loud.

```
voice in  ->  Saaras v4, mode="verbatim", keyterms = the household's medicine names
          ->  Utterance stored: their exact words, kept separate from any summary
          ->  sarvam-105b with the README's strict json_schema -> four factors, one tier, one reason
          ->  tier ratchet: max(previous, proposed), +1 step on doubt, never downward
          ->  sarvam-105b reply  ->  refusal validator
          ->  Mayura v1 (modern-colloquial)  ->  Bulbul v4 Flash, pace 0.8
          ->  voice out, as a WAV under out/
```

Real output from a live run, a Telugu voice note from the parent:

| | |
|---|---|
| Heard, verbatim | `అమ్మ అంటోంది కాళ్ళు వాచాయి మూడు రోజుల నుంచి` |
| Language | `te-IN`, confidence `1.0` |
| Tier | `critical`, `escalated: true` |
| Ratchet | the model asked for a human; critical tier always reaches a human |
| Spoken back | `అమ్మకి మూడు రోజులుగా కాళ్ళు ... నేను ఎవరితో మాట్లాడాలి?` |

`GET /agent/conversation/{episode_id}` returns the turns in order, both speakers,
with the verbatim record intact.

## 2. The agent calls the clinic — `POST /clinic/call`

The agent speaks to the clinic's receptionist, holds the slot, and then hands the
parent the line so they confirm their own appointment by name.

Implemented behaviour, each with a test: no answer or busy redials the same
clinic once, then falls to the rank-2 clinic, then reports the dead end; no slot
in the requested window takes the next option and records which and why; a
booking cannot reach `confirmed` without `confirmed_by_name`; an agent line that
breaks a refusal ends the call and escalates.

**What is real and what is not.** `transport="telephony"` posts to the actual
Indus instant-outbound endpoint and raises `IndusNotConfigured` naming the
missing variables — it never fabricates an `attempt_id`. `transport="local"`
(the default) is the path that runs today: the agent's own lines are generated
live by `sarvam-105b-conversations` and genuinely pass the refusal validator, but
the receptionist and the parent's confirmation are read from
`fixtures/clinic_receptionist.json`. No phone line is involved. Every response
carries its `transport`, so a local run cannot be read back as a real call.

To place a real call, add to `.env`: `SARVAM_VA_API_KEY`, `SARVAM_ORG_ID`,
`SARVAM_WORKSPACE_ID` — plus a number rented in Indus → Deploy → Phone Numbers
(Vobiz, after KYC). `call_transfer` works end to end only on Vobiz and Plivo.

## The invariants, and where they are enforced

| Rule | Where |
|---|---|
| Never names a condition, suggests a dose, or substitutes a medicine | `assess/refusal.py`, run on every agent-authored string before it is stored, spoken or sent |
| The person's verbatim words are **not** validated | `api/talk.py` — the parent may say "my sugar is high"; their words stand, and are never put in a notification |
| Severity only escalates | `assess/tier.py` — no path can return a tier below the one it was given |
| Role-based visibility | `notify/roles.py` — the family-group text is built from a template, so a rupee figure has no slot to reach them through |
| The key stays server-side | `config.py` is the only reader; `/healthz` reports `key_present`, never the key |

## Running it

```
cp .env.example .env            # then paste SARVAM_API_KEY
./run.sh                        # http://localhost:8000/docs
./test.sh                       # 73 tests, no network calls
```

Without a key, every wrapper serves a recorded fixture and tags the response
`source: "mock"`, so a mock can never pass for a real transcription.

## Verified against the installed SDK

`sarvamai==0.1.37`. Every signature used was checked by introspection, not
assumed: `speech_to_text.transcribe`, `speech_to_text_job.create_job`,
`chat.completions` (including `response_format` and `reasoning_effort`),
`text.translate`, `text_to_speech.convert`.

One documentation discrepancy, resolved empirically: the SDK's docstring says
`mode` applies only to `saaras:v3`. A round-trip test (Bulbul-generated Telugu
speech, transcribed twice) shows the modes differ on `saaras:v4` — `verbatim`
omits the formatting punctuation that `transcribe` adds — so the README is right
and the docstring is stale. Whether `verbatim` retains spoken fillers is still
unconfirmed, because synthesised speech does not reliably contain any.

## Left open

- `# OPEN:` in `assess/refusal.py`: the second refusal layer (a strict-boolean
  `sarvam-105b` check) sits behind the same `validate()` signature, unbuilt.
- `# OPEN:` in `voice_agents/platform.py`: the `app_config` field shapes come
  from the specification's prose, not from a live API reference, and no Indus
  workspace exists to confirm them against.
- Substitution detection has no medicine-name NER; it compares against the
  household's prescribed list, so a misspelled brand name could slip past.
- No authentication on any route, and the store is in memory — see
  `docs/DEPLOY.md` before exposing a public URL.
