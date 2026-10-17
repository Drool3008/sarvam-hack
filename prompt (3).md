# Build prompt — Family Health Agent

Attach this file and `README.md` to your coding agent (Claude Code, Cursor or similar) and say: "Read prompt.md and README.md, then start with Milestone 0." Sarvam recommends giving coding tools its MCP server rather than a pasted reference, so connect it first (see Setup).

---

## 1. Role and objective

You are the lead engineer building **Family Health Agent**, a household app with an agent inside it that keeps an ageing parent's medicines, appointments and records running. `README.md` is the product specification. Build the product in the milestones below, in order. Each milestone ends with working code, passing tests, and a short note of what was built and what is left.

## 2. Rules that override everything else

1. **`README.md` is the source of truth.** Build what it describes. If this file and the README disagree, follow the README and say so. If neither covers a decision, choose the simplest option, mark it `# DECISION:` in the code, and list it in the milestone note.
2. **The three refusals are invariants.** No code path, prompt, tool or message may name a condition, suggest a dose, or substitute a medicine. Each of those goes to a human through `escalate_to_human`. Every model output that reaches a person passes the refusal validator (section 8) first.
3. **Severity only escalates.** If the factors disagree or the agent cannot tell, the tier goes up and a human is asked. No code lowers a tier on its own.
4. **Days of cover come from the dispensed quantity, never from the prescription.** Every days-of-cover figure stores where it came from.
5. **Role-based visibility.** The family group sees status only. The responsible person sees full detail and every rupee. The doctor sees the assembled record. The notification layer enforces this, not the caller.
6. **Only Sarvam calls listed in the README.** Use only the SDK methods, endpoints and model IDs in the README's "Stage-by-stage API backing" table and "Appendix: Sarvam API surface used". Check each signature against the installed SDK (`sarvamai`, `sarvam-conv-ai-sdk`) or the Sarvam MCP server before using it. Never invent a parameter.
7. **Out of scope:** WhatsApp as an agent channel, voice cloning, waiting through hold music, warm or three-way transfers, live diarization, the Responses API, Dubbing, and Content Studio.
8. **Secrets stay server-side.** No Sarvam key in the mobile or web client. Live voice sessions go through the backend.
9. **No placeholder data in production paths.** Seed data lives only in `fixtures/` and tests.

## 3. Setup

- **Sarvam accounts:** an API subscription key for the model APIs from the Sarvam dashboard, and an Indus workspace (indus.sarvam.ai) with `org_id`, `workspace_id` and a workspace API key for the Voice Agents platform.
- **Sarvam MCP server in the coding tool:** runs through `uvx` and needs Python 3.11+. Use `sarvam_code_*` for docs and endpoint shapes, and `sarvam_tools_*` to try calls. It is a build-time aid only and is not part of production.
- **SDKs:**
  - `pip install sarvamai sarvam-conv-ai-sdk` (checked against `sarvamai` 0.1.37 and `sarvam-conv-ai-sdk` 1.1.1).
  - For the app: `sarvam-conv-ai-sdk/react-native`, or Flutter `sarvamconv_ai_sdk`.
- **Telephony:** rent a number in Indus → Deploy → Phone Numbers (Vobiz, after KYC), or bring Plivo or Vobiz. Call transfer works end to end only on these two.

**Environment variables**

```
SARVAM_API_KEY=            # model APIs (sarvamai)
SARVAM_VA_API_KEY=         # Voice Agents platform, sent as X-API-Key
SARVAM_ORG_ID=
SARVAM_WORKSPACE_ID=
SARVAM_VA_BASE_URL=https://apps.sarvam.ai
DATABASE_URL=
REDIS_URL=
WEBHOOK_SHARED_SECRET=     # checked on every inbound webhook and hook call
PUBLIC_BASE_URL=           # where Sarvam reaches our hooks, tools and webhooks
```

## 4. Default stack (DECISION — change only with a reason)

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy plus Alembic, PostgreSQL.
- **Background jobs:** a worker with a Redis-backed queue (for example `arq`) for document jobs, batch speech-to-text jobs, campaign building, and the contact-chain state machine.
- **App:** React Native (Expo) for the household app, with the voice-agent SDK for the Household assistant.
- **Family web view:** a minimal page with the Sarvam widget snippet.
- **Tests:** `pytest`, with Sarvam calls mocked at the wrapper boundary.

```
family-health-agent/
  backend/
    app/
      api/            # REST for the app; hooks, tools and webhooks for Sarvam
      domain/         # households, people, medicines, dispenses, episodes, wallet
      cover/          # days-of-cover engine
      assess/         # assessment prompt, schema, refusal validator
      notify/         # role-based notifications + translation
      sarvam/         # one thin wrapper per Sarvam call (the only place the SDK is imported)
      voice_agents/   # deployments, campaigns, instant outbound, analytics clients
      workers/        # background jobs
    migrations/
    tests/
    fixtures/
  app/                # React Native household app
  web/                # family view with widget
  agents/             # exported Indus agent configs, system prompts, test cases (versioned here)
```

## 5. Data model

The fields come from the README. Field names are a DECISION.

- **Household:** `id`, `city_pair` (Tier 1 city, Tier 2 city), `created_at`.
- **Person:** `id`, `household_id`, `name`, `phone_e164`, `preferred_language` (BCP-47, for example `te-IN`), `second_language`, `reads_roman_script` (bool), `roles` (set of `affected`, `responsible`, `family_group`), `consent_given_at` (required before any data about them is stored).
- **ContactChainEntry:** `household_id`, `person_id`, `rank` (who can make a sound decision, not age).
- **Condition:** `person_id`, `label` (stored as entered by the family; never generated or shown by the agent).
- **RedFlag:** `household_id`, `person_id`, `text`.
- **Medicine:** `id`, `person_id`, `name`, `strength`, `dose_per_day` (number), `duration`, `prescriber`, `prescribed_on`, `source_extraction_id`.
- **Dispense:** `id`, `medicine_id`, `quantity`, `dispensed_on`, `chemist_id`, `source` (`receipt` or `manual`), `receipt_file_ref`, `extraction_id`, `confidence`, `sources_json`, `confirmed_by_person_id`, `confirmed_at`.
- **Extraction:** `id`, `kind` (`prescription`, `receipt`, `report`), `job_id`, `result_json`, `annotations_json`, `status`.
- **Provider:** `id`, `city`, `type` (`clinic`, `chemist`, `lab`), `name`, `phone_e164`, `hours`, `booking_notes`, `rank` (two of each per household, ranked).
- **TestSchedule:** `person_id`, `name`, `interval_days`, `next_due_on`.
- **WalletPolicy:** `household_id`, `limit_inr`, `ask_above_inr`.
- **Transaction:** `id`, `household_id`, `episode_id`, `amount_inr`, `status` (`held`, `needs_approval`, `paid`, `refused`), `approved_by`, `counterparty`.
- **Episode:** `id`, `household_id`, `affected_person_id`, `trigger_kind` (`affected_person`, `family_member`, `agent_clock`), `source_person_id`, `tier`, `factors_used`, `reason`, `escalated`, `account_type` (`firsthand`, `secondhand`), `stage` (one of the ten stages), `status`, `opened_at`, `closed_at`.
- **Utterance:** `id`, `episode_id`, `verbatim_text`, `language`, `speaker_label`, `audio_ref`, `stt_job_id`. Kept separate from summaries and never sent in notifications.
- **Summary:** `episode_id`, `text_en`, `created_from` (`voice_note`, `call`).
- **Call:** `id`, `episode_id`, `agent` (`intake`, `check_in`, `clinic`, `chemist`), `attempt_id`, `interaction_id`, `to_phone`, `status` (`connected`, `no_answer`, `busy`, `failed`), `duration`, `final_agent_variables`, `recording_ref`.
- **Booking:** `episode_id`, `provider_id`, `slot`, `confirmed_by_name`, `status`.
- **Order:** `episode_id`, `chemist_id`, `medicine_id`, `quantity`, `recipient_person_id`, `received_by_person_id`, `status`.
- **Notification:** `audience` (`family_group`, `responsible_person`, `doctor`), `person_id`, `language`, `text`, `audio_ref`, `episode_id`.
- **AuditEvent:** an append-only log of every agent action, with the actor and the data source.

## 6. Days-of-cover engine (`cover/`)

- `days_of_cover = sum(quantity of dispenses since cover began) / dose_per_day`. Worked example from the README, which must be a test: 20 tablets at two a day is 10 days. The 60 tablets on the prescription must not produce 30.
- The refill date is `dispensed_on + floor(days_of_cover)`. It is recomputed on every new dispense.
- With no recorded dispense, days of cover is `unknown`, and the agent asks the responsible person for the receipt (DECISION). It never falls back to the prescription quantity.
- Every figure returns with `provenance` (dispense IDs, receipt refs, confidence, who confirmed).

## 7. Sarvam wrappers (`sarvam/`)

One function per call, typed inputs and outputs, retries with backoff on `TooManyRequestsError`, and other `ApiError`s raised as domain errors. Nothing outside `sarvam/` and `voice_agents/` imports the SDK.

```python
from sarvamai import SarvamAI
from sarvamai.errors import TooManyRequestsError
from sarvamai.core.api_error import ApiError

client = SarvamAI(api_subscription_key=settings.SARVAM_API_KEY)

# Onboarding / Closing: prescription and receipt extraction (async job)
job = client.doc_ai.extract(file=[image_bytes], schema=PRESCRIPTION_SCHEMA_JSON, output_format="json")
# poll client.doc_ai.get_status(job.job_id) until completed / partially_completed / failed / rejected
results = client.doc_ai.get_results(job_id)          # result + annotations (confidence, sources per leaf)

# Onboarding: old reports
job = client.doc_ai.digitise(file=[pdf_bytes], language="te-IN")
md = client.doc_ai.get_results(job_id, format="md")

# Triggered: short voice note (<= 30 s)
r = client.speech_to_text.transcribe(file=audio, model="saaras:v4", mode="verbatim",
                                     keyterms=household_medicine_names[:50])

# Triggered / Listening: long note or call recording, with diarization
job = client.speech_to_text_job.create_job(model="saaras:v4", mode="verbatim",
                                           with_diarization=True)   # always pass model explicitly
job.upload_files([path]); job.start(); job.wait_until_complete()

# Assessing
resp = client.chat.completions(
    model="sarvam-105b", messages=msgs, tools=TOOLS, tool_choice="auto",
    response_format=ASSESSMENT_RESPONSE_FORMAT, reasoning_effort="high", max_tokens=8192)

# Checking in: messages and speech
t = client.text.translate(input=text, source_language_code="en-IN", target_language_code=lang,
                          model="mayura:v1", mode="modern-colloquial")
a = client.text_to_speech.convert(text=native_script_text, language_code=lang,
                                  model="bulbul:v4-flash", pace=0.8, dict_id=household_dict_id)
```

- Prescription schema fields: medicine name, strength, frequency, duration, prescriber, date. Receipt schema fields: medicine, quantity dispensed, date, chemist.
- Every extracted leaf below the confidence threshold (DECISION: start at 0.85) goes to the responsible person to confirm. Nothing low-confidence is auto-filled.
- Doc AI limits: 10 pages per PDF, 10 requests per minute. Queue document jobs in the worker.
- `max_tokens` must stay well above the reasoning budget, because reasoning tokens count toward it.
- Mayura takes 1,000 characters per request. Use `sarvam-translate:v1` (2,000 characters) for languages outside Mayura's 11, and never pass it `output_script` or `numerals_format`.
- TTS takes native script only, up to 2,500 characters, with no SSML.
- Use `sarvam-105b` for backend reasoning and `sarvam-105b-conversations` inside the live agents. Never use `sarvam-m` or `sarvam-30b`.

## 8. Assessment and the refusal validator (`assess/`)

- Use the tool list and the assessment `response_format` exactly as written in the README ("Agent tools" and "Assessment output schema"). `factors_used` may contain only the four factors.
- The prompt gives the model the trigger, the verbatim text, the summary, the person's known conditions and medicines (for matching only), the red-flag list, and context (time, distance, who is reachable, wallet left).
- **Refusal validator (DECISION on method).** It runs on every model output before a person sees it, and as a backstop on every HTTP tool argument from the live agents. A violation means the output is discarded, `escalate_to_human` runs, and an AuditEvent is written. It has two layers:
  - **Deterministic:** dose patterns (numbers with mg, ml, tablet, times a day), any medicine name not already prescribed for that person (substitution), and the household's condition labels or a condition lexicon appearing in agent-authored text.
  - **Model check:** a second `sarvam-105b` call with a strict boolean schema: names a condition, suggests a dose, or suggests a substitute.
- **Tier ratchet:** a new tier is `max(previous tier, model tier)`. On disagreement or low certainty the tier goes up one step and `escalated = true`.

## 9. Voice agents (`agents/` and `voice_agents/`)

Build the five agents from the README's agent roster in Indus. Keep each system prompt, greeting, variables list and test cases in `agents/<name>/` so they are versioned with the code.

| Agent | Deployment | Backend endpoints it needs |
|---|---|---|
| Intake | Inbound deployment on the household number | `POST /hooks/on-start` (caller number → household, role, language, medicine names, red flags), `POST /hooks/on-end`, HTTP tool `POST /tools/raise-episode` |
| Check-in | Instant outbound + daily campaign | hooks; HTTP tools `GET /tools/days-of-cover`, `POST /tools/escalate` |
| Clinic | Instant outbound | hooks; HTTP tool `POST /tools/book-slot`; `call_transfer` to variable `affected_person_phone` |
| Chemist | Instant outbound | hooks; HTTP tools `POST /tools/check-stock`, `POST /tools/order-medicine`, `POST /tools/pay-from-wallet` (gated in a confirm state; returns `needs_approval` above `ask_above_inr`) |
| Household assistant | React Native / Flutter SDK, web widget | backend proxy for sessions; read-only tools scoped to the asking person's role |

- **Every hook and tool endpoint:** checks the shared secret, is idempotent on `attempt_id` or `interaction_id`, answers fast, and writes an AuditEvent.
- **Live-call system prompt:** start from the README's "System prompt skeleton for the live-call agent". Add per-agent goals only.
- **Language personalisation:** start in the person's `preferred_language`, allow switching, and use `second_language` where Bulbul v4 Flash or Voice Agents does not cover the first (see the README's language coverage).

**Platform clients (`voice_agents/`)**

All calls go to `https://apps.sarvam.ai` with header `X-API-Key`.

- `create_inbound_deployment()`: `POST /api/app-authoring/v1/orgs/{org_id}/workspaces/{workspace_id}/deployments`
- `create_campaign()` and `upload_cohort()`:
  - `POST /api/scheduling/v1/orgs/{org_id}/workspaces/{workspace_id}/campaigns` with `allowed_schedule.timezone = "Asia/Kolkata"`, `retry_config` and `webhook_config`
  - `POST .../campaigns/{campaign_id}/cohorts/upload` (multipart: `name`, `cohort_file` CSV, `cohort_transformation_file` JSON)
- `place_call(agent, to_phone, variables)`: `POST /api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds`. Confirm in the API reference how agent variables are passed before relying on them.
- `get_transcript(interaction_id)` and `get_recording(interaction_id)`: `GET /api/analytics/v1/{org_id}/{workspace_id}/{app_id}/transcripts|recordings/{interaction_id}`. The recording comes back as WAV bytes, not JSON.
- `run_test_suite(test_suite_id)`: `POST /api/evals/v1/{org_id}/{workspace_id}/test-suites/{test_suite_id}/runs`.

**Webhooks and the contact chain (`workers/`)**

- **Instant-outbound webhook:** if `status != connected`, move to the next rank in the contact chain and place the next call. On a critical tier, place calls to the affected person and the responsible person at the same moment. If everyone is unreachable on a critical tier, dispatch anyway and keep calling, as the README's stage table says.
- **On-end hook or webhook with an `interaction_id`:** fetch the recording, run Saaras v4 batch (`mode="verbatim"`, `with_diarization=True`), store Utterances, and set `account_type = secondhand` when the main speaker is not the affected person.
- **Clinic does not answer:** redial, then try the second clinic, then report the dead end.
- **No slot:** take the next option and say which one and why.
- **Out of stock:** go to the next chemist, never a substitute.
- **Spend above the limit:** stop and ask. With no answer, hold the booking unpaid; do not cancel it.

## 10. Notifications (`notify/`)

- `notify_family_group` sends status and who did what only. It strips medical detail by construction: it builds from a status template, not from free text.
- `notify_responsible_person` sends full detail and every rupee.
- **Translation:** Mayura in `modern-colloquial` mode, Roman output script for members who read in Roman script, and Sarvam-Translate for other languages.
- **Spoken version for the parent:** Bulbul v4 Flash with the household `dict_id`.

## 11. Milestones and acceptance criteria

**Milestone 0: Skeleton**
- Repo layout, config, database migrations for section 5, the Sarvam wrappers with mocks, health checks, and CI running tests.
- Done when CI is green, wrappers have unit tests, and the API key is only read server-side.

**Milestone 1: Onboarding, days of cover, voice-note intake** (README Phase 1)
- Household setup in one sitting: people, roles, consent per adult, contact chain, languages, wallet limit and ask-above figure, two clinics, chemists and labs each, red flags.
- The prescription photo goes through `doc_ai.extract`, then a confirmation screen for low-confidence fields. The chemist receipt goes through `doc_ai.extract` to create a Dispense with provenance.
- Days of cover and refill dates per medicine. Voice notes are transcribed verbatim, with a separate English summary. Notifications are role-filtered and translated.
- Must prove: days of cover from the dispensed quantity is right on every fixture receipt. Tests cover 20 tablets at two a day giving 10 days, unknown cover without a dispense, and low-confidence fields never auto-filled.

**Milestone 2: Calls, hand-off, doctor record** (README Phase 2)
- Intake, Check-in and Clinic agents built in Indus, with hooks and tools live. Instant outbound, the contact-chain state machine, and call transfer to the parent.
- Post-call verbatim record with diarization. Assessment with the strict schema, the refusal validator and the tier ratchet. Doctor record through `sarvam-105b`, with Document Translation when the doctor's language differs.
- Must prove: the Clinic agent holds a slot with a real receptionist and bridges the parent onto the call in the parent's language, on Vobiz or Plivo.
- Sarvam test suites for each agent pass: refuses condition, dose and substitute; never lowers a tier.

**Milestone 3: Ordering, wallet, campaigns** (README Phase 3)
- Chemist agent with gated payment, the wallet policy enforced in `pay_from_wallet`, and the daily campaign for refill and test dates (cohort upload, DND, retries, webhook processing).
- Closing writes the next refill date from the dispensed quantity. Household assistant in the app and the web widget.
- Must prove: no payment above `ask_above_inr` without approval, verified by tests and by Sarvam test cases. Every rupee appears in the responsible person's view. Every episode closes with slot confirmed by name, medicine received by a named person, family told, and next refill date set.

## 12. Testing

- **Unit:** the cover engine, contact chain, tier ratchet, refusal validator (positive and negative cases in English and in at least Hindi and Telugu), wallet policy, and role filter.
- **Contract:** each Sarvam wrapper against recorded responses. Hook and tool endpoints against the payloads in the Sarvam webhook docs.
- **Agent:** Sarvam Tests (test suites and cases in `agents/<name>/tests`), run in CI through the evals endpoint before any agent version is committed for deployment.
- **Manual:** one end-to-end episode per milestone on a real number, recorded in the milestone note.

## 13. Open questions

The open questions are those in the README's "Constraints and open questions" list. Do not settle any of them by assumption. Build behind an interface, mark it `# OPEN:`, and raise it in the milestone note.
