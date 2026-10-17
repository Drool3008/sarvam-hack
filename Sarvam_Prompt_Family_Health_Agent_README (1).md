# Prompt for Sarvam AI — Family Health Agent README

Paste everything below the line into Sarvam (Indus chat, or the API playground with `sarvam-105b`). If the reply stops partway through, send: "Continue exactly from where you stopped. Do not repeat earlier sections."

---

## ROLE

You are a senior product manager and solutions architect writing an idea proposal for a product called **Family Health Agent**. You also know Sarvam AI's model and agent platform well. You will write one file, `README.md`, that works as a complete idea proposal. A mentor, a hackathon or incubator panel, or an engineering team should be able to read it and understand the problem, the product, how it behaves, and exactly how it would be built on Sarvam AI.

## WHAT YOU ARE GIVEN

1. **SOURCE A**: the full text of the concept note "Family Health Agent" (PDF).
2. **SOURCE B**: the full text of the pitch deck "Family Health Agent" (5 slides), by Dhawal P, mentor Ramesh Loganathan.
3. **SOURCE C**: a capability sheet for Sarvam AI, taken from docs.sarvam.ai in October 2026.

Everything you write must trace back to one of these three sources.

## HARD RULES (follow all of them)

1. **Never invent facts.** Every statistic, percentage, price, survey number, competitor name, and product behaviour must come from SOURCE A or B. Every Sarvam model name, parameter, limit, language list, and price must come from SOURCE C. If a number is not in the sources, do not write it.
2. **Label what is new.** The sources describe the product. They do not describe how it is built on Sarvam. When you propose architecture, tool definitions, schemas, or build phases that the sources do not state, put **(Proposed)** at the start of the section heading or table caption. Do not label product behaviour that the sources already state.
3. **Keep the product's own vocabulary exactly:** *affected person, responsible person, contact chain, family group, days of cover, wallet, wallet limit, ask-above figure, red-flag list, tier, secondhand, dispensed quantity, the loop, Watch / Reach / Assess / Act and Close*. Define each once, then use it consistently.
4. **Keep the three refusals intact everywhere.** The agent never names a condition, never suggests a dose, and never substitutes a medicine. Each of those goes to a human. No Sarvam component you describe may break these rules. Where an LLM is involved, say how the rule is enforced: system prompt, output schema, validation tool, or a human hand-off.
5. **Severity only escalates.** If factors disagree or the agent cannot tell, it goes up a tier and asks a human. It never guesses downward. Keep this in the architecture too.
6. **Style:** direct, plain, professional English, using Indian conventions (₹, lakh/crore if needed). State things plainly. No hedging or meta phrases ("it is worth noting", "this is almost certainly", "arguably"). No marketing adjectives. No emojis. No "Prepared by" line, no date header, no author block beyond one credit line at the very end. Prefer prose over tables. Use tables only where the source itself is a table (the ten stages, the competitor comparison) or where comparing many items across the same columns (the stage-to-Sarvam mapping, language coverage).
7. **Open questions go in one short list at the end**, not woven into the prose.
8. **Formatting:** valid GitHub-flavoured Markdown. One H1. H2 for main sections, H3 for subsections. Include one Mermaid diagram of the loop and one Mermaid diagram of the system architecture. Put code, JSON schemas, and tool definitions in fenced code blocks.
9. **Be as detailed as the sources allow, and no more detailed.** Depth comes from explaining mechanics fully (the dispensed-quantity example, every failure mode, every stage, every Sarvam component's job and limits), not from padding.

10. **Build only on what Sarvam supports today.** The README must not use, propose, or mention the following, not even as limits, open questions, or future options:
    - WhatsApp as an agent channel. The agent works through phone calls and the household app. The segment description may still say the parent uses WhatsApp on a smartphone, because that is a fact about the user.
    - Voice cloning of any kind.
    - Waiting through hold music, or detecting when a person answers after hold.
    - Warm transfer, three-way conference calls, or the agent staying on the line after a transfer.
    - Live (real-time) diarization.
    - Bulbul v4 Flash in Malayalam or Odia.

    Where the sources describe one of these, write the supported version instead:
    - "Sits through the hold" becomes: the Clinic agent speaks with the clinic's receptionist, holds the slot, then uses `call_transfer` to bridge the parent onto the line to confirm it by name.
    - "Calls the person and the responsible person together" on a critical tier becomes: two outbound calls placed at the same moment.
    - Speaker separation always runs on the recording after the call.

11. **Every Sarvam functionality must be backed by an API or an agent configuration listed in SOURCE D.** Each time the README says a Sarvam component does something, it must name the SDK method or endpoint, or the Indus agent configuration, that does it. If SOURCE D does not list a call for a functionality, leave that functionality out. Do not invent endpoints, methods, parameters or model IDs.

## REQUIRED README STRUCTURE

Write the sections in this order.

**# Family Health Agent**
One-line tagline taken from the sources.

**## Summary**
One paragraph: the problem, the product, the user, what makes it different, and that it is built on Sarvam AI's Indic speech, language, document, and voice-agent stack.

**## The problem**
- The core insight: "Nobody finds out the medicine is over until it is over."
- Primary research: the September 2026 survey (25 people, 10 Indian families). Give every figure: 21, 23, 2, 12, 5 of 9. Include the "history gets lost when someone new is handling it" point.
- Secondary evidence with sources named inline: UNFPA India Ageing Report 2023, WHO India, National Health Accounts 2022-23.
- The market gap: today's options sell hands or delivery. Nothing sells coordination.
- The single-point-of-failure child, and the parent who gave up the errands but not the choices.

**## Who it is for**
The Tier 1 to Tier 2 city pair (son in Hyderabad, mother in Warangal). Payer profile and parent profile. Why this pair beats metro-to-metro and non-resident children. Growth one city pair at a time, and why.

**## What it is**
- One household app with an agent inside it.
- Onboarding in one sitting.
- **### The four roles**: affected person, responsible person (wallet and veto, used only on disagreement), contact chain (ranked by who can make a sound decision, not by age), family group (sees that something happened, never the medical detail).
- **### What it takes in** and **### What it gives back**: full lists from the sources.
- **### What it will not do**: the three refusals.

**## How it works**
- **### The loop**: Watch → Reach → Assess → Act and Close → back to Watch, as a Mermaid flowchart.
- **### Triggers**: only three kinds (the affected person, another family member, the agent's own clock). Show the severity range within each kind of trigger, using the source examples.
- **### How severity is assessed**: the four factors, citing which were used, one line of reasoning, and escalation on doubt.
- **### The ten stages and their failure modes**: a table with columns Stage | What it does | When it breaks, reproduced faithfully from SOURCE A Figure 2. Then a sentence stating the principle that every failure moves to the next option, holds, or hands back to a human, and none stops silently.
- **### The core mechanic: counting from what was dispensed**: the full worked example (20 tablets at two a day = 10 days of cover, against 60 on the prescription implying 30; a prescription clock runs out 20 days late). Explain why that is the worst direction to be wrong in, and that the agent records where its number came from.
- **### The phone call, not the room**: the agent calls the clinic, works out the slot with the receptionist, then bridges the parent onto the call through call transfer. The parent confirms their own appointment in their own language.

**## (Proposed) Built on Sarvam AI**
This is the main new section. Make it the most detailed part of the README.
- **### Why Sarvam**: tie it to the sources. The parent speaks a language other than English. Clinics and chemists in smaller cities are reached by phone, not by app. Voice notes arrive in whatever language the family uses. Code-mixed speech is normal. Then the SOURCE C facts that matter: 22 Indian languages plus English in speech and documents, code-mix handling, telephony-native voice agents, and data including PII staying in India.
- **### Stage-by-stage API backing**: the core table of the README. Columns: Stage | Functionality | Sarvam model | API call (SDK method and endpoint) | Key parameters and limits. Cover all ten stages, in order, and reproduce every row of SOURCE D. Keep method names, endpoint paths, model IDs and parameter values exactly as SOURCE D gives them, in inline code. Where a stage has no Sarvam call (for example, the days-of-cover arithmetic in Idle), say "Product backend" in the API column rather than leaving it blank. After the table, add one short paragraph explaining the three kinds of backing: Model APIs (`sarvamai` SDK, `https://api.sarvam.ai`), Voice Agents platform APIs (`https://apps.sarvam.ai`, `X-API-Key` header), and agent configuration built in Indus and run by Sarvam's voice-agent runtime (call transfer, hooks, HTTP and code tools, knowledge base, states), which is deployed through the platform APIs.
- **### Model catalogue fit**: a table with columns Model | Function in Sarvam's catalogue | Job in this product | Fit. Use one of two values for Fit: **Core**, or **Core with limits** (name the limit). Cover these rows: Bulbul v4 Flash (streaming TTS), Bulbul v4 Flash (REST TTS), Saaras v4 (real-time STT), Saaras v4 (batch with diarization), Sarvam-105B, Sarvam-105B-conversations, Sarvam Vision, Mayura v1, Sarvam-Translate v1, Transliteration, Language Identification, Document Translation. Take the verdicts from the FEASIBILITY VERDICTS section below.
- **### Voice agents on Indus**: the second-largest section. Describe how the product runs on Sarvam's voice agent platform at indus.sarvam.ai, in this order:
  - **#### Agent roster (Proposed)**: Sarvam calls multi-state "an older paradigm" and is moving to multi-agent setups, so the product uses several narrow agents instead of one large one. Define each: **Intake agent** (inbound; the parent or a family member calls in to raise something), **Check-in agent** (outbound; calls the affected person, the responsible person and down the contact chain), **Clinic agent** (outbound; calls the clinic, books, and hands the parent the line through call transfer), **Chemist agent** (outbound; checks stock, places the order, and moves to the next chemist if it is out of stock), and **Household assistant** (in-app voice and chat, through the SDK or widget, so "anyone can ask the agent instead of phoning the one person who always knows"). For each agent give: trigger, deployment type, tools, variables loaded by the on-start hook, what the on-end hook writes back, and which refusals and escalations it must enforce.
  - **#### Phone numbers**: rent from Sarvam (Vobiz partner account, KYC first, 30-day auto-renewing rental paid from Sarvam credits) or bring your own provider. Recommend Vobiz or Plivo, because call transfer works end to end only on those. Note that a rented number is released, and its deployments and campaigns cancelled, with no grace period if credits run short. The design must keep a credit floor.
  - **#### Inbound**: one household number assigned to the Intake agent. The on-start hook looks up the caller's number and loads the household, the person's role, preferred language, current medicines (names only, for recognition) and red-flag list into variables. A caller from an unknown number is treated as "another family member raises it" and verified before any detail is shared.
  - **#### Outbound campaigns**: for clock-triggered work. A daily cohort CSV of households whose refill or test date is due, with per-contact variables (name, medicine, days of cover left, preferred language). Uses the org-wide DND list, schedules, retries, and the per-attempt webhook (outcome, transcript, duration, collected variables) that updates the record. The default limit is 10 concurrent campaigns.
  - **#### Instant outbound calls (API)**: for triggered episodes. The orchestrator places a call and reads the webhook for that attempt. If the call does not connect, it places the next call down the contact chain. On a critical tier it places two calls at once, to the affected person and the responsible person.
  - **#### Deploy with code**: the household app embeds the Household assistant using the React Native or Flutter SDK. The family view on the web uses the widget snippet. Live sessions use WebSocket through the product's backend, because API keys never go in client code. The Python SDK (`sarvam-conv-ai-sdk`) is used for server-side sessions.
  - **#### Workflows (multi-state, used narrowly)**: used only in the Clinic and Chemist agents, to gate tools by phase. For example, `pay_from_wallet` is available only after the slot or order is confirmed and the amount is checked against the ask-above figure. States read and write shared variables so nothing is asked twice.
  - **#### Tools**: HTTP (API) tools for single lookups and actions (days of cover, book slot, order, notify). Code tools (Python, available on request) for multi-step fallbacks, such as next chemist, then second clinic, then report the dead end. Call transfer (`call_transfer` to an E.164 number held in a variable, so the destination is the parent's own number). The Data Validator (alpha) for phone numbers collected on calls. Mocking for tests.
  - **#### Knowledge base**: Sarvam says the knowledge base is not for personal account data. So it holds only non-personal, local content: each city pair's clinic, chemist and lab directory (hours, phone, how to book) and the product's own operating policies. Personal medical data comes in only through hook variables and tools.
  - **#### Tests and versioning**: write test cases that try to make each agent name a condition, suggest a dose, substitute a medicine, spend above the limit, or guess a lower tier, and require it to refuse or escalate. Deploy only committed versions.
  - **#### Monitoring**: Agent Analytics, call transcripts and recordings, the log analyser, and Boards serve as the audit trail behind "every rupee to the responsible person".
  - **#### Verbatim record from calls (Proposed)**: the live agent's transcript is not guaranteed to be verbatim. After each call, the on-end hook passes the recording reference to Saaras v4 **batch** in verbatim mode with diarization. That produces the word-for-word record, separates who spoke, and supports marking an account secondhand.
- **### Component deep-dives**: one H4 per component (Saaras, Bulbul, Sarvam-105B, Sarvam Vision / Doc Agents, Mayura / Sarvam Translate / Transliteration / Language Identification, Document Translation, Voice Agents platform, MCP server). For each, say what job it does in this product, which mode or parameter to use and why, and the limits from SOURCE C that shape the design.
- **### Language coverage**: a table of the languages a family might use, with columns for Saaras (hear), Bulbul v4 Flash (speak), Voice Agents (live call), and the text and document models, filled only from SOURCE C. Then state the design consequence plainly: some languages can be heard and read but not yet spoken back or handled on a live call. Say what the agent does in that case (for example, text in the language plus a call in the person's second language, or a hand-off to a family member). Mark this behaviour **(Proposed)**.
- **### System architecture**: a Mermaid diagram showing the household app, the agent orchestrator (Sarvam-105B with tool calling), Voice Agents telephony, Saaras, Bulbul, Vision / Doc Agents, the translation layer, the household record store, the wallet / payments, and the external parties (clinics, chemists, labs, doctor). Payments, the record store, and the chemist and clinic directories are not Sarvam services. Show them as the product's own systems or third-party systems. Do not claim Sarvam provides them.
- **### Agent tools**: define the tools the orchestrator calls, as OpenAI-style `tools` function definitions in JSON. Sarvam-105B supports `tools` with `type: "function"` and `tool_choice`. Derive each tool from a behaviour the sources state, for example `get_days_of_cover`, `place_call`, `transfer_call_to_affected_person`, `book_slot`, `order_medicine`, `pay_from_wallet` (which refuses above the ask-above figure and returns `needs_approval`), `notify_family_group` (status only), `notify_responsible_person` (full detail and every rupee), `build_doctor_record`, `set_next_refill_date`, `escalate_to_human`. Leave out any tool that would diagnose, dose, or substitute, and say so.
- **### Assessment output schema**: a `response_format` of type `json_schema` with `strict: true` for the Assess stage. Fields: `trigger_kind`, `source` (who raised it), `tier`, `factors_used` (array from the four factors only), `reason` (one line), `escalated` (boolean), `account_type` (firsthand or secondhand), `verbatim_transcript_ref`, `summary`. Add a short validation rule: reject any output that contains a condition name, a dose, or a substitute suggestion, and escalate instead.
- **### System prompt skeleton for the live-call agent**: a fenced block for `sarvam-105b-conversations`. It covers role, the four roles, the three refusals, escalate-on-doubt, hand the line to the parent, keep the person's words verbatim, and speak in the person's preferred language at a slower pace.
- **### Privacy and consent by design**: consent per adult at onboarding, the split between the family group and the responsible person and doctor, verbatim speech kept separately from the summary, data residency in India (SOURCE C), and the self-hosted deployment option.
- **### Cost drivers**: two or three sentences of prose, no table. Name which Sarvam meters scale with usage (speech-to-text per hour, TTS per 10K characters, document extraction per page, LLM tokens, voice-agent minutes) and quote the SOURCE C rates for the ones it lists. Do not invent usage volumes or a per-household total. State that voice-agent per-minute pricing is not published and must be confirmed.

**## Where it sits**
The competitor comparison from SOURCE A Figure 3 as a table (staffed eldercare, senior apps, pharmacy apps, Family Health Agent; rows: what they sell, where they stop, who it is for). Then the three things that make it hard to copy.

**## Who pays**
₹199 a month per household in the current concept, free for the first three months, with the wallet kept separate. The three later revenue lines: non-resident families, clinics and chemists, and insurers.

**## (Proposed) Build phases**
A short, ordered phasing that stays inside source scope. For example: Phase 1 is onboarding with prescription and receipt extraction plus days of cover, notifications, and voice-note intake. Phase 2 is outbound clinic calls with hand-off to the parent, booking, and the doctor record. Phase 3 is ordering and payment within the wallet, the full contact chain, and campaigns for refill dates. Each phase names the Sarvam components it switches on and the one thing it must prove. Keep it to prose or a short list.

**## Constraints and open questions**
One short bulleted list. Include at least:
- Language gaps between Saaras, Bulbul v4 Flash, and Voice Agents.
- Bulbul v3 reaches end of life on Voice Agents on 10 November 2026, so build on v4 Flash.
- The payments and wallet partner, and pharmacy and clinic integrations, are outside Sarvam.
- How the call hand-off (call transfer) bridges the parent onto a clinic call.
- The survey sample size (25 people, 10 families) and the need to validate further.
- Credit floor: a rented number is released, and its deployments cancelled, when Sarvam credits run short.
- Alpha and on-request features: code tools are available on request, and the Data Validator and Verifier are in alpha.
- Handwritten prescriptions: extraction accuracy on Indian handwritten prescriptions needs testing on real samples before launch.

**## Appendix: Sarvam API surface used**
A flat, grouped list of every SDK method and endpoint the product calls, taken from SOURCE D, under these headings: Speech to text, Text to speech, Chat, Text processing, Document intelligence, Document translation, Voice Agents platform, Voice-agent SDKs, Agent configuration (Indus). One line per call: the method or endpoint in inline code, then a few words on what the product uses it for. End with the list of Sarvam surfaces that are deliberately not used: the Responses API, Dubbing, and Content Studio.

**## Sources**
List: the survey (September 2026), UNFPA India Ageing Report 2023, WHO India, National Health Accounts 2022-23, docs.sarvam.ai.

End with one line: `Concept by Dhawal P · Mentor: Ramesh Loganathan`.

## MAPPING GUIDANCE (use it to build the Sarvam section; do not paste it verbatim)

- **Onboarding, prescription photo**: Sarvam Vision through Doc Agents **Extract**. Prescriptions are a listed document type. Write a schema for medicine name, strength, frequency, duration, prescriber, and date. Each field returns a confidence score. Low-confidence fields go to the responsible person to confirm, never auto-filled. Supported files are PDF, JPEG, PNG, up to 50 MB and 10 pages per project. Save it as a reusable **Config**.
- **Dispensed quantity**: Doc Agents **Extract** on the itemised chemist receipt (receipts are a listed type) to read the quantity actually handed over. This is the technical heart of the core mechanic. Store the quantity with its provenance (receipt image, extracted value, confidence, who confirmed it).
- **Old handwritten reports**: Doc Agents **Digitise** into Markdown or HTML for the household record.
- **Preferred language at onboarding**: Language Identification. Saaras also returns `language_probability` when the language is left as unknown.
- **Listening to voice notes**: Saaras (v4 default). Use **verbatim** mode to keep the person's exact words, as the product requires. Use **codemix** mode for mixed speech. Use **translate** mode to produce the English summary for the doctor. Use **keyterm prompting** (up to 50 terms, v4, REST and batch only) loaded with the household's medicine names. REST takes up to 30 seconds per request, batch up to 2 hours, and streaming goes over WebSocket. Use **batch diarization** to separate speakers when someone else speaks for the affected person, which supports marking the account secondhand.
- **Speaking**: Bulbul v4 Flash (Hindi, English, Hinglish, Bengali, Gujarati, Kannada, Marathi, Punjabi, Tamil, Telugu). Set `pace` between 0.5 and 2.0, slower for elderly listeners. Write Indic text in native script, not romanised. There is no SSML. REST takes up to 2,500 characters. Use the MCP server's **pronunciation dictionary management** so medicine and clinic names are said correctly.
- **Reaching and acting by phone**: Sarvam **Voice Agents**. Inbound and outbound calls run on Sarvam or rented numbers, or through Exotel, Twilio, Plivo, and others. Use **API tools** to call booking and ordering systems, **call transfer** for the hand-off to the parent and to humans, several narrow agents rather than one multi-state agent (multi-state only to gate payment tools), **on-start and on-end hooks** to write to the record, a **knowledge base** for each household's clinic and chemist list, **campaigns** with DND handling for scheduled refill and test calls, and **instant outbound calls through the API** for triggered episodes. Calls can last up to 60 minutes. **Agent Analytics**, call logs, and the log analyser serve as the audit trail. Data, including PII, stays in India.
- **Reasoning and orchestration**: `sarvam-105b` (128K context) for assessment and the doctor record, and `sarvam-105b-conversations` (32K) for real-time calls. Use `tools`, `response_format` json_schema, and `reasoning_effort`. Do not set a small `max_tokens` while reasoning is on.
- **Family group and responsible-person messages in each member's language**: Mayura or Sarvam Translate for short text. Use transliteration for members who read their language in Roman script.
- **Doctor record and reports**: Document Translation, which preserves layout, for PDF and Office reports, up to 12 target languages per job. This covers a doctor in another state or a family member who reads another language.
- **Building it**: the Sarvam MCP server (`sarvam_tools_*` and `sarvam_code_*`) and the official Python and JS SDKs (`sarvamai`). Framework integrations include LiveKit, Pipecat, Vapi, LangChain, and n8n.
- **Out of scope**: Dubbing, Content Studio, voice cloning and the coding agent. Do not mention them.

## FEASIBILITY VERDICTS (use these for the "Model catalogue fit" table and the voice-agent section)

- **Bulbul v4 Flash, streaming (HTTP or WebSocket, 8–24 kHz)**: **Core.** Low-latency speech for the in-app Household assistant and spoken status read-outs to the parent. Limit: hi, en, en-hi, bn, gu, kn, mr, pa, ta, te only. Households whose members speak only other languages get messages in text through Mayura or Sarvam-Translate, and calls in a second language the person names at onboarding.
- **Bulbul v4 Flash, REST**: **Core.** Pre-rendered voice messages, such as "your tablets arrive today", sent to the parent in their language. Up to 2,500 characters per request, native script, and a slower `pace`.
- **Saaras v4, real-time (REST up to 30 s, WebSocket streaming)**: **Core.** Short voice notes and live in-app speech. Keyterms take the household's medicine names (REST only, not streaming).
- **Saaras v4, batch with diarization**: **Core with limits.** Handles voice notes longer than 30 s and every call recording after the call: verbatim transcript, speaker labels, timestamps. Runs after the call. Costs ₹45 per hour against ₹30 without diarization.
- **Sarvam-105B**: **Core.** The orchestrator: tool calling, the strict JSON assessment output, and the doctor record (128K context). Limit: 10 Indian languages plus English, so input in other languages is translated before reasoning.
- **Sarvam-105B-conversations**: **Core.** The model behind the live voice and chat agents (32K context).
- **Sarvam Vision**: **Core with limits.** Reads prescriptions, chemist receipts and old reports, with field extraction and confidence scores through Doc Agents Extract. Limits: 10 pages per PDF, 10 requests per minute, and handwriting confirmed for Doc Agents Digitise but not stated on the Vision model page. Low-confidence fields always go to the responsible person to confirm.
- **Mayura v1**: **Core.** Family group and responsible-person messages in each member's language. Use the modern-colloquial or code-mixed mode for a natural tone, Roman output script for members who read their language in English letters, and numeral control for amounts and dates. Limit: 11 languages and 1,000 characters per request.
- **Sarvam-Translate v1**: **Core with limits.** Fallback for the languages Mayura does not cover (all 22 scheduled languages, 2,000 characters per request), for example Maithili or Konkani.
- **Transliteration and Language Identification**: **Core.** Detect each person's language at onboarding, and handle romanised typing.
- **Document Translation**: **Core with limits.** Carries the doctor record or a report into another language with its layout preserved. Used only when the doctor or the responsible person reads a different language.
- **Indus voice-agent features**: Agents, inbound, phone numbers, outbound campaigns, instant outbound API, deploy with code, SDKs, tools, knowledge base, hooks, variables, tests, versioning and analytics are all **Core**. Multi-state workflows are **Core with limits** (a legacy paradigm, so use them only to gate tools). Code tools are **Core with limits** (access on request). The Data Validator and Verifier are **Core with limits** (alpha).

---

## SOURCE A — Concept note: "Family Health Agent"

A household agent that keeps an aging parent's medicines, appointments and records running, so that no one in the family has to remember.

**The problem**
Nobody finds out the medicine is over until it is over.
In a survey of 25 people across 10 Indian families in September 2026, 21 had someone at home on a lifelong daily medicine. 23 of them found out a medicine was finished by counting what was left in the strip, or on the day it ran out. Only 2 had ever had a doctor's visit that began because a refill was due. The supply of a medicine that must not be missed is tracked by eye, by one person, usually from another city.
That person is almost always an adult child. 12 of the 25 said their parent no longer phones the clinic at all: a child books the slot, orders the medicines and answers the doctor's questions on their behalf. But of the parents in the sample, 5 of 9 said they still want to be asked first. They had given up the errands, not the choices. A respondent named the second cost: history gets lost when someone new is handling it.
The scale behind this is not in dispute. India's elderly share of population is projected to pass 20% by 2050, growing about 41% a decade, with the 80-and-over group growing roughly 279% between 2022 and 2050 (UNFPA, India Ageing Report 2023). About 1/4 Indian adults have hypertension and only around 12% have it under control (WHO India). Households carry much of the cost themselves: out-of-pocket spending was 49.9% of current health expenditure in the 2022-23 National Health Accounts.
The work is real, recurring, and lands on a family member with no tools for it. What exists today sells either hands (nurses, attendants, emergency response) or delivery (pharmacy apps). Nothing sells the coordination.

**What it is**
One app for a household, with an agent inside it that treats the family's health as a standing responsibility rather than a series of errands. One person sets it up: installs it, adds the others, photographs a prescription, and sets a spending limit. That is the whole of onboarding.
Four roles shape every decision the agent makes. The affected person is whoever needs care. The responsible person owns the wallet and holds a veto, used only when they and the affected person disagree. The contact chain is ranked by who can make a sound decision, not by age. The family group sees that something happened, never the medical detail, which goes only to the responsible person and the doctor.
What it takes in: one prescription photo, the known conditions and current medicines, a ranked contact chain, each person's preferred language, a wallet limit and the figure above which it must ask before spending. After that, voice notes and messages from the family in whatever language they use, and its own clock reaching a refill or test date.
What it gives back: a real days-left figure per medicine, counted from what was actually dispensed; a clinic slot booked and confirmed by name, with the parent on the line; medicine ordered, paid within the limit and delivered to a named recipient; status to the family group and full detail with every rupee to the responsible person; and one assembled record for the doctor covering summary, last reports, current medicines and the trend.
Three things it will not do, by design: it never names a condition, never suggests a dose, and never substitutes a medicine. Each of those goes to a human.

**How it works**
Ten stages, which fold into four phases.
Figure 1. The loop: WATCH (Days of cover on every medicine, recurring test dates. Nothing to do.) → REACH (The affected person first, the responsible person in parallel, then down the chain.) → ASSESS (Four factors, one tier, one reason. Never a diagnosis.) → ACT AND CLOSE (Book, order, pay, deliver, tell the family, set the next refill date.)
Something starts the loop in one of three ways, and only those three: the affected person sends a voice note or message, another family member raises it, or the agent's own clock reaches a date its data produced. Each kind of trigger spans a range of severity. A medication trigger can be a finished antibiotic course or a blood-pressure tablet with no stock nearby. A test can be a one-off swab or a panel a doctor wants within hours. An emergency can be a mild flu or an ambulance.
Severity is worked out, not tagged. At the assessing stage the agent weighs four things: whether what was said matches the family's red-flag list, whether it is new or worsening for this person, whether it touches a medicine they already take, and the context of time, distance, who is reachable and money left. It cites which of the four it used and gives one line of reasoning. If the factors disagree, or it cannot tell, it goes up a tier and asks a human. It never guesses downward.

Figure 2. The ten stages and what each does when it fails.

| Stage | What it does | When it breaks |
|---|---|---|
| Onboarding | Family, conditions, medicines, red flags, two clinics, chemists and labs each, languages, wallet limit, consent per adult. | — |
| Idle | Watch days of cover and recurring test dates. | — |
| Triggered | Tags the kind of trigger and a first severity, with the source named. | Nobody answers the trigger: it moves to the next contact rather than waiting. |
| Reaching | Call the affected person, tell the responsible person at the same time. | No answer: works down the ranked chain. On a critical tier it calls the person and the responsible person together. |
| Listening | Keeps what was said word for word, in their language, and writes a separate short summary. | The person cannot describe it: whoever is present speaks, and the account is marked secondhand for the doctor. |
| Assessing | Follow-up questions against known conditions and medicines, then a tier with its reasons. | Cannot tell: treats it as urgent and asks a human. Critical with nobody reachable: dispatches anyway and keeps calling. |
| Acting | Book the slot, order the medicine, arrange transport, and pay from the wallet. | The clinic will not answer: redials, tries the second clinic, then reports the dead end. No slot: takes the next option and says which and why. Out of stock: next chemist, never a substitute. |
| Checking in | Runs alongside the rest. Status to the family group, spend and detail to the responsible person. | Spend above the limit: stops and asks. No answer: holds the booking unpaid rather than cancelling it. |
| Handing over | Send the doctor one record: summary, last reports, current medicines, the trend. | Wrong specialist: carries the same record into the new booking. |
| Closing | Slot confirmed by name, medicine received by a named person, family told who did what, next refill date set. | — |

The loop closes on what was dispensed, not what was prescribed, and that is the single most important mechanic in the product. People routinely buy only what the week's cash covers. Twenty tablets handed over at two a day is ten days of cover, where the sixty on the prescription would have implied thirty. A clock set from the prescription runs out twenty days late, which is the worst direction to be wrong in. The agent therefore reads the quantity off the counter, not the paper, and records where its number came from.

**Where it sits**
Figure 3. Four ways of serving the same household, and where each one ends.

| | Staffed eldercare (Samarth, Emoha, Portea, KITES) | Senior apps (Khyaal, GenWise) | Pharmacy apps (Tata 1mg, PharmEasy, Apollo 24/7) | Family Health Agent |
|---|---|---|---|---|
| What they sell | People and presence: care managers, attendants, nurses, emergency response, errand help. | Engagement with the senior: community, digital literacy, reminders, an assistant. | Delivery, with refill reminders attached to the order. | Coordination for a household that is already coping. |
| Where they stop | At the staff. Cost rises with every family served, so the service is priced for the top of the market. | At a reminder. No authority to spend, call or book, and the senior has to open the app. | At the order. No view of the family, no appointment, no record, and the count comes from the prescription. | It acts, within a limit the family sets, and reports back. |
| Who it is for | Mostly non-resident children buying staffed care for a parent in India. | The senior, as the user and often the payer. | Anyone ordering medicine. | The adult child in a Tier 1 city with a parent in a smaller one. |

The gap is narrow and specific. Staffed operators can do everything this agent does, because a person does it, but a person costs money every time and the model therefore sells to households that can pay several thousand rupees a month. Senior apps reach the parent but hold no authority, so the most they can do is tell someone that something is due. Pharmacy apps hold the transaction but not the family: they know what was ordered, not who it was for, whether it arrived, or what the doctor said next.
Three things make this product hard to copy from any of those three positions. It counts cover from the dispensed quantity, which needs the itemised receipt rather than the order. It places the call and hands the parent the line, which keeps the parent in the decision rather than replacing them in it. And it is built for several people in one household at once, with a wallet, a veto and a status feed, where every competitor is built for one user at a time.

**Who it is for**
The first segment is a pair of cities, not a city. The payer is an adult child between 25 and 40, salaried, living in a Tier 1 city. The parent is 60 or over, in a Tier 2 city or smaller, on at least one daily medicine, using WhatsApp on a smartphone, and speaking a language other than English at home. A son in Hyderabad and a mother in Warangal is the shape of it.
That pairing is chosen over the two obvious alternatives. Metro to metro is too close: the child can drive over on a Saturday, so the problem resolves itself badly but it resolves. Non-resident children pay more and are the natural second market, but they are already served by staffed operators, and buying hands is a reasonable answer when you are eight time zones away. The Tier 1 to Tier 2 pair is where the distance is too far to drive and too near to justify hiring someone, where the clinic and the chemist are small, local and reached by phone rather than by app, and where the parent's language is the first thing most products get wrong.
Growth follows the same logic: one city pair at a time, because the clinics and chemists have to be known for the agent to be useful, and that knowledge is local.

**Who pays**
The adult child, who is already paying for all of it. One household subscription covers every member at ₹199 a month in the current concept, free for the first three months, with the wallet kept separate and spent only within a limit the family sets. Three later lines follow from the same product without changing it: non-resident families, who pay more for the same reassurance; clinics and chemists, for appointments and refills that arrive scheduled rather than as walk-ins; and insurers, for whom a medicine that never lapses is cheaper than the admission that follows one that did.

---

## SOURCE B — Pitch deck: "Family Health Agent" (Dhawal P · Mentor: Ramesh Loganathan)

**Slide 2 — At a glance.** Parents' medicines, appointments and reports — handled, without anyone having to remember. Nobody finds out the medicine is over until it is over. An adult child in one city manages an ageing parent's health in another, over phone calls. Nothing watches how many days of a daily medicine are actually left. Nothing holds the family's prescriptions, reports and history in one place. The one child who keeps track becomes the single point of failure, and the parent, having handed over the errands, slowly loses the decisions with them. The Family Health Agent watches the supply of every medicine, calls the clinic and sits through the hold, orders and pays within a limit the family sets, and tells everyone what happened.
- In a survey of 25 people across 10 Indian families, 21 had someone at home on a lifelong daily medicine — and 23 found out it was finishing by counting the strip, or on the day it ran out.
- 12 of the 25 said their parent no longer phones the clinic at all; a child does it. But of the parents asked, 5 of 9 said they still want to be asked first.
- India's elderly share of population is projected to pass 20% by 2050, growing 41% a decade. About one in four Indian adults has hypertension, and roughly 12% have it under control.

**Slide 3 — What it does.** One prescription in, a household that keeps itself running. One person in the family is the responsible person: they install the app, add the others, photograph a prescription and set a spending limit. That is the setup. From then on the agent watches, reaches, decides, acts and reports on its own. It speaks to each person in their own language. The parent keeps every decision that is theirs to make. The family group sees that things happened; only the responsible person and the doctor see the detail.
What it takes in: one prescription photo, the known conditions and the current medicines; a ranked contact chain, and each person's preferred language; a wallet limit, and the amount above which it must ask before spending; voice notes and messages from the family, in whatever language they use; its own clock reaching a refill date or a recurring test date.
What it gives back: a real days-left figure per medicine, counted from what was actually dispensed; a clinic slot booked and confirmed by name, with the parent on the line; medicine ordered, paid within the limit, delivered to a named recipient; status to the family group, full detail and every rupee to the responsible person; one record for the doctor: summary, last reports, current medicines, the trend.

**Slide 4 — How it works.** Watch, reach, decide, act — then set the next clock. WATCH → REACH → ASSESS → ACT AND CLOSE → back to watching.
In plain terms: the agent sits quietly and counts. It knows each person's dose and how many tablets were actually handed over, so the days-left number is real rather than an estimate. When something needs doing — a voice note arrives, or its own clock reaches a refill date — it calls the person it concerns, with the responsible person told at the same time, and works down the contact list if nobody picks up. It listens in the person's own language and keeps their words exactly as they said them; it writes a separate short summary, and marks the account secondhand if someone else had to speak for them. It then weighs four things — whether this matches the family's red-flag list, whether it is new or worsening for this person, whether it touches a medicine they already take, and the context of time, distance and money left — and puts the case into a tier with a one-line reason. It never names a condition and never suggests a dose. If the factors disagree, or it cannot tell, it goes up a tier and asks a human rather than guessing downward. Then it acts: calls the clinic, waits on hold, hands the parent the line when a person picks up, orders the medicine, pays within the limit and stops to ask above it. Every failure moves to the next option, holds, or hands back to a human — none of them stops silently. The episode closes when the medicine reaches the person it was for, and the agent sets the next refill date from the quantity actually dispensed, so the loop starts again without anyone remembering anything.

**Slide 5 — Why it matters.** The errands move. The decisions stay. Indian eldercare sells hands — nurses, attendants, emergency response — and pharmacy apps sell delivery. Neither sells the coordination that the family already coping is actually doing by hand.
- *Counts cover, not reminders.* It works out days of cover from the quantity actually dispensed at the counter, not the quantity written on the prescription. People routinely buy only what that week's cash covers. A clock set from the prescription runs out late, which is the worst direction to be wrong in.
- *Takes the phone call, never the room.* It calls the clinic, sits through the hold, and hands the parent the line when a person picks up. The parent confirms their own appointment, in their own language. The child loses the logistics without the parent losing the choice.
- *One household, not one app each.* Every action appears in the family view, so the sibling who did nothing still knows the tablets arrived and who received them. Anyone can ask the agent instead of phoning the one person who always knows.
Who pays: the adult child who is already paying for all of it. One household subscription covers every member — ₹199 a month in the concept, free for the first three months — while the wallet stays the family's own money, spent only within a limit they set. Beyond that: non-resident children, who pay more for the same reassurance and today buy it as staffed care; clinics and chemists, for appointments and refills that arrive scheduled rather than walk-in; and, in time, insurers, for whom a medicine that never lapses is cheaper than the admission that follows one that did.

---

## SOURCE C — Sarvam AI capability sheet (docs.sarvam.ai, October 2026)

**Models**
- **Saaras (STT)**: v4 is the default, and v3 is still available. Covers 22 Indian languages plus English: Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Nepali, Konkani, Kashmiri, Sindhi, Sanskrit, Santali, Manipuri (Meitei), Bodo, Maithili, Dogri. Modes: transcribe (default, with formatting and number normalisation), translate (English output), verbatim (keeps fillers and spoken numbers as said), translit (Roman script), and codemix (English words stay English, Indic words in native script). REST takes up to 30 s per request. Batch takes up to 2 h per file. Streaming runs over WebSocket. Diarization (speaker labels with timestamps) is batch only. `with_timestamps` gives chunk-level timestamps. Language detection returns `language_probability` when the language is unknown. Keyterm prompting takes up to 50 terms on v4, REST and batch only. Accepts most audio formats, including OGG and OPUS (WhatsApp voice notes) and AMR.
- **Bulbul (TTS)**: v4 Flash covers hi, en, en-hi, bn, gu, kn, mr, pa, ta, te, with 200+ persona voices. v3 has 11 languages, including Malayalam and Odia, with 30+ voices. `pace` ranges from 0.5 to 2.0. There is no SSML, and Indic text should be in native script. REST takes 2,500 characters per request. Streaming runs over HTTP and WebSocket at 8–24 kHz. Bulbul v3 reaches end of life on Voice Agents on 10 November 2026.
- **Sarvam-105B (chat)**: 128K context, with reasoning on by default. `sarvam-105b-conversations` is the real-time dialogue and voice-agent variant, with 32K context. Chat Completions supports `tools` (function), `tool_choice`, `response_format` (`json_schema` with `strict`, `json_object`, `text`), `stream`, `reasoning_effort` (low/medium/high/max), `max_tokens`, and `seed`. Reasoning tokens count toward `max_tokens`. Covers the top 10 Indian languages plus English, in native script, romanised, and code-mixed input.
- **Mayura / Sarvam Translate (text translation)**: Mayura covers 11 languages (10 Indian plus English). Also available: transliteration and language identification.
- **Sarvam Vision (document intelligence)**: OCR and structured output across 23 languages.

**Products**
- **Doc Agents**: **Extract** turns plain-English field descriptions into an editable schema. It returns a value, a confidence score, and a not-found placeholder per field, with inline correction. Listed document types include invoices, receipts, KYC, statements, insurance claims, and **prescriptions**. Exports JSON, CSV, or XLSX. **Digitise** handles scans, handwriting, tables, and multilingual documents, exporting HTML, Markdown, DOCX, or TXT. Reusable Configs (12 templates). Accepts PDF, JPEG, PNG, up to 50 MB and 10 pages per project.
- **Document Translation**: translates PDF and Office files into up to 12 Indian languages per job, preserving layout and format.
- **Voice Agents**: inbound and outbound phone calls in a real-time STT → LLM → TTS loop. Works with Sarvam or rented numbers, or with your own provider (Exotel, Twilio, Smartflo, Plivo, Vobiz, Pulse, Intalk). Channels: telephony, web voice and chat widget, API, and SDKs (Python, Web, React Native, Flutter). Languages: Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Assamese, English. Handles code-mixed speech, alphanumerics, and proper nouns. Tools: core tools, call transfer, API tools, data validation and verification, mocking, code tools. Also: multi-state agents, variables and personalisation, knowledge base, on-start and on-end hooks, versioning, and tests. Campaigns support cohorts, dialing rate, concurrency, and DND handling. Instant outbound calls can be placed through the API. Agent Analytics covers connectivity, engagement, tools, goals, call logs, and a log analyser, with custom Boards and webhooks. Maximum call length is 60 minutes. Speech recognition, reasoning, and synthesis are self-hosted by Sarvam, and data including PII stays in India.
- **Voice Agents on Indus (indus.sarvam.ai), in more detail**:
  - **Build:** Agents are built on a Canvas, either drafted by Genie from a description or created from scratch. Each agent has a greeting, a system prompt, variables, language personalisation (starting language, switching during a call, allowed languages) and a speaker voice. A test-agent mode is available before deploy. Deploys use committed versions only.
  - **Multi-state:** each state has its own instructions, gated tools and allowed transitions, with shared variables across states. Sarvam calls it "an older paradigm" it is moving away from in favour of multi-agent setups, and recommends single-state unless tools must be gated by phase.
  - **Phone Numbers:** bring your own provider, or rent from Sarvam through its Vobiz partner account. Renting needs KYC (Individual or Corporate), runs for 30 days, auto-renews, and is charged to Sarvam credits. If credits fall short, the number is released and its campaigns and deployments are cancelled, with no grace period. Number groups support rotation. `080` and `079` landlines need a `0` or `+91` prefix.
  - **Inbounds:** assign a number to an agent to answer incoming calls.
  - **Campaigns:** take a CSV cohort, one contact per row, with personalisation fields mapped to variables. You set a schedule, and calls retry. The dialing rate (CPS) and concurrency are configurable, with a default limit of 10 concurrent Active or Scheduled campaigns. An org-wide DND suppression list applies. Lifecycle states are Active, Paused, Scheduled, Ended and Cancelled. A webhook fires per call attempt, connected or not, with outcome, transcript, duration and collected variables.
  - **Instant outbound API:** `POST /api/outbounds/v1/orgs/:org_id/workspaces/:workspace_id/outbounds` with `app_config` (agent id, version, connection, agent phone number), `user_config.user_phone_number`, and an optional `webhook_config`. Returns an `attempt_id`.
  - **Deploy with code:** API recipes to create or update agents, start voice or text sessions, trigger outbound calls with variable payloads, and fetch transcripts and outcomes. Real-time WebSocket sessions carry audio frames, turn events and tool-call signals; proxy them through your backend and never expose API keys in client code. A web widget is embedded by snippet. SDKs: Python `sarvam-conv-ai-sdk`, Web `sarvam-conv-ai-sdk/browser`, React Native, Flutter `sarvamconv_ai_sdk`.
  - **Tools:** core tools, call transfer, HTTP/API tools for single lookups, code tools (Python classes extending `SarvamTool`, with access to secrets and agent variables, can make HTTP calls, available on request), Data Validator and Data Verifier (alpha), and tool mocking.
  - **Call transfer:** the `call_transfer` tool bridges the live call to an E.164 number or SIP URI, which can be static or held in a variable. It works on phone calls only, and end to end on Vobiz and Plivo; Exotel needs the Sarvam team. The destination must answer, or the transfer fails.
  - **Knowledge base:** accepts PDF, DOCX, CSV, TXT and MD, and returns reranked chunks of about 500 tokens tagged by source file. The agent routes between knowledge bases by their descriptions. Sarvam states it is not meant for personal account data.
  - **Hooks:** the on-start hook runs before the call (inputs typically include the caller's number and campaign metadata) and returns fields mapped to variables, which can gate tools or states. The on-end hook pushes disposition, collected fields, and transcript or recording references.
  - **Tests:** written test cases, runs, and reviewed results.
  - **Monitoring:** Agent Analytics with transcripts and recordings per call.
- **Mayura v1 (detail)**: 11 languages, translating both ways with English, with an `auto` source. Modes: formal, modern-colloquial, classic-colloquial, code-mixed. Output script can be Roman, native or spoken, and numeral format is controllable. 1,000 characters per request. **Sarvam-Translate v1** covers all 22 scheduled languages at 2,000 characters per request.
- **Sarvam Vision (detail)**: a 3B vision-language model. Extracts text from PDFs and scans, converts tables to HTML or Markdown, and keeps layout and reading order. Takes PDF, PNG, JPG, or a flat ZIP of up to 10 images. Async jobs through `client.doc_ai.digitise(...)`, then `get_status`, then `get_download_url`. Output is HTML or Markdown plus page-level JSON. Limits: 10 pages per PDF, 200 MB per file, 10 requests per minute.
- **Developer tools**: MCP server (`sarvam_tools_*` for runtime tasks, including STT, TTS, translation, transliteration, language ID, chat, document extraction and digitisation, and **pronunciation dictionary management**; `sarvam_code_*` for docs and starter code). Official `sarvamai` Python and JS/TS SDKs. Integrations: LiveKit, Pipecat, Vapi, Twilio, Exotel, LangChain, Vercel AI SDK, n8n. Self-hosted deployment is available.

**Pricing (INR)**
- Sarvam-105B: ₹15 per 1M input tokens, ₹5 cached, ₹60 output.
- STT: ₹30 per hour, or ₹45 with diarization.
- TTS (Bulbul v3): ₹30 per 10K characters.
- Translation and transliteration: ₹20 per 10K characters.
- Language ID: ₹3.5 per 10K characters.
- Document extraction: ₹1 per page. Digitisation: ₹0.5 per page.
- Document translation: ₹5 per 1K characters per target language.
- Voice-agent per-minute pricing is not published.
- New accounts get ₹100 in credits.

---

## SOURCE D — Sarvam API backing by stage (checked against the `sarvamai` Python SDK v0.1.37, `sarvam-conv-ai-sdk` v1.1.1, and the Voice Agents API reference)

**Conventions**
- **Model APIs:** use the `sarvamai` SDK (`from sarvamai import SarvamAI`; `client = SarvamAI(api_subscription_key=...)`). REST base `https://api.sarvam.ai`; WebSocket base `wss://api.sarvam.ai`.
- **Voice Agents platform APIs:** base `https://apps.sarvam.ai`, with header `X-API-Key: <workspace API key>`. `{org_id}` and `{workspace_id}` are path parameters.
- **Agent configuration:** built in Indus (indus.sarvam.ai → Build), run by Sarvam's voice-agent runtime, and deployed only as committed versions through the Deployments, Campaigns and Instant-outbound APIs.
- **Model IDs in the SDK:**
  - Speech to text: `saaras:v3`, `saaras:v4`
  - Text to speech: `bulbul:v2`, `bulbul:v3`, `bulbul:v4-flash`
  - Translation: `mayura:v1`, `sarvam-translate:v1`
  - Chat: `sarvam-105b`, `sarvam-105b-conversations`
- **Speech-to-text `mode` values:** `transcribe`, `translate`, `verbatim`, `translit`, `codemix`.
- **Translate `mode` values:** `formal`, `modern-colloquial`, `classic-colloquial`, `code-mixed`.

**1. Onboarding**
- *Prescription photo to structured medicines:* model Sarvam Vision. Call `client.doc_ai.extract(file=[...], schema='<JSON schema>', output_format="json")`, which maps to `POST /doc-ai/v1/job/extract`. Then poll `client.doc_ai.get_status(job_id)` (`GET /doc-ai/v1/job/{job_id}/status`) until it is `completed`, `partially_completed`, `failed` or `rejected`, and fetch the output with `client.doc_ai.get_results(job_id)`.
  - Results hold `result` plus `annotations`, where every leaf has `confidence` and `sources`. Fields below the confidence threshold go to the responsible person to confirm.
  - Schema rules: the root is `type: "object"`, every field has a `type` and a `description`, and nesting goes at most 4 levels deep. A saved Config can be passed as `config_id` instead of `schema`.
  - Limits: 10 pages per PDF, 10 requests per minute.
- *Several photos at once:* call `client.doc_ai.create_upload_url(...)` (`POST /doc-ai/v1/job/upload`), then pass `upload_ids` to `extract`.
- *Old reports into the household record:* model Sarvam Vision. Call `client.doc_ai.digitise(...)` with `language` and `output_format` (HTML or Markdown), then `client.doc_ai.get_download_url(job_id)`.
- *Each person's preferred language:* call `client.text.identify_language(input=...)` (`/text-lid`).
- *Correct pronunciation of medicine, clinic and family names:* call `client.pronunciation_dictionary.create(...)`, which returns a `dict_id` that is passed to text to speech.
- *Household inbound number:* the number is rented (Vobiz, after KYC) or connected in Indus → Deploy → Phone Numbers. Assign it to the Intake agent with `POST https://apps.sarvam.ai/api/app-authoring/v1/orgs/{org_id}/workspaces/{workspace_id}/deployments`, sending `name`, `app_id`, `app_version`, `connection_configs`, `inbound_config` (`start_time`, `end_time`, `allowed_days`, `timezone`) and `webhook_config`.

**2. Idle (Watch)**
- *Days of cover per medicine and recurring test dates:* computed in the product backend from the dispensed quantity. There is no Sarvam call.
- *Daily clock-triggered calls:* create a campaign with `POST https://apps.sarvam.ai/api/scheduling/v1/orgs/{org_id}/workspaces/{workspace_id}/campaigns`.
  - Send `name`, `app_config` (`app_id`, `app_version`, `attempts_per_second`, `connection_configs`, `retry_config`, `webhook_config`), `start_timestamp`, `end_timestamp`, and `allowed_schedule` (`allowed_start_time`, `allowed_end_time`, `allowed_days`, `timezone: "Asia/Kolkata"`).
  - Upload the day's cohort with `POST .../campaigns/{campaign_id}/cohorts/upload` (multipart: `name`, `cohort_file` CSV, and a `cohort_transformation_file` JSON that maps CSV columns to the phone number and agent variables).
  - The org-wide DND list applies. The default limit is 10 concurrent campaigns.

**3. Triggered**
- *Voice note of 30 seconds or less:* model Saaras v4. Call `client.speech_to_text.transcribe(file=..., model="saaras:v4", mode="verbatim")`. Leave `language_code` out to get `language_probability`. Pass `keyterms` with the household's medicine names (up to 50 terms).
- *Voice note longer than 30 seconds:* model Saaras v4, batch. Call `client.speech_to_text_job.create_job(model="saaras:v4", mode="verbatim", with_diarization=True, num_speakers=...)`, then `start()`, `get_status()` and `get_download_links()`. The endpoint family is `speech-to-text/job/v1`. Files can be up to 2 hours.
- *Typed message:* call `client.text.identify_language(...)`. If the language is outside Sarvam-105B's 10 Indian languages plus English, call `client.text.translate(..., model="sarvam-translate:v1")` first.
- *First tag and severity:* model Sarvam-105B. Call `client.chat.completions(model="sarvam-105b", messages=[...], response_format={"type": "json_schema", "json_schema": {"name": "...", "schema": {...}, "strict": true}})`, which maps to `POST /v1/chat/completions`.

**4. Reaching**
- *Call the affected person, then down the contact chain:* call the Check-in agent with `POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds`, sending `app_config` (`app_id`, `app_version`, `connection_config.connection_id`, `agent_phone_number`), `user_config.user_phone_number` and `webhook_config`. It returns an `attempt_id`.
  - The webhook returns a `status` of `connected`, `no_answer`, `busy` or `failed`, plus `interaction_id`, `duration`, `final_agent_variables` and `interaction_transcript` (`role`, `en_text`). Any status other than `connected` makes the backend place the next call in the chain.
  - On a critical tier, two outbound calls go out at the same moment.
- *Tell the responsible person at the same time:* a push notification from the product. The text comes from `client.text.translate(model="mayura:v1", ...)`.

**5. Listening**
- *The live conversation:* the agent runtime (Saaras, `sarvam-105b-conversations` and Bulbul inside the agent), with language personalisation set in the agent.
- *Word-for-word record:* fetch the recording with `GET https://apps.sarvam.ai/api/analytics/v1/{org_id}/{workspace_id}/{app_id}/recordings/{interaction_id}`, which returns a WAV file. Run it through `client.speech_to_text_job.create_job(model="saaras:v4", mode="verbatim", with_diarization=True)`. The diarized transcript gives the exact words and the speaker labels used to mark an account secondhand.
- *Short English summary:* use the `interaction_transcript` `en_text` from the webhook, or `GET .../transcripts/{interaction_id}`, summarised by `client.chat.completions(model="sarvam-105b")`.
- *In-app voice intake:* call `client.speech_to_text_streaming.connect(model="saaras:v4", ...)` (`wss://api.sarvam.ai/speech-to-text/ws`).

**6. Assessing**
- *Four factors, one tier, one reason, escalate on doubt:* call `client.chat.completions(model="sarvam-105b", messages, tools=[{"type": "function", ...}], tool_choice, response_format={"type": "json_schema", ..., "strict": true}, reasoning_effort="medium", max_tokens=...)`. Set `max_tokens` high enough, because reasoning tokens count toward it.
- *Follow-up questions on a call:* the agent runtime, using `sarvam-105b-conversations`. Variables come from the on-start hook (agent configuration).

**7. Acting**
- *Clinic call, booking, and hand-off to the parent:* call the Clinic agent through the instant-outbound endpoint above.
  - In the call, HTTP tools (agent configuration) call the product's `book_slot` API.
  - The `call_transfer` core tool (agent configuration) bridges the call to the parent's E.164 number held in an agent variable. This works on Vobiz or Plivo, and the destination must answer.
- *Stock check and order:* call the Chemist agent through instant outbound, with HTTP tools for `check_stock` and `order_medicine`. Code tools (a Python `SarvamTool` class, available on request) handle the next-chemist fallback.
- *Payment within the wallet:* the product's own wallet and payment partner. The `pay_from_wallet` HTTP tool is gated in a confirm state (multi-state agent configuration), so it runs only after confirmation.

**8. Checking in**
- *Family group status in each member's language:* model Mayura v1. Call `client.text.translate(input=..., source_language_code="en-IN", target_language_code="te-IN", model="mayura:v1", mode="modern-colloquial", output_script=..., numerals_format=...)` (`/translate`). Up to 1,000 characters.
- *Fallback for the other scheduled languages:* call `client.text.translate(..., model="sarvam-translate:v1")`. Up to 2,000 characters. `output_script` and `numerals_format` are ignored here.
- *Members who read their language in Roman script:* call `client.text.transliterate(...)` (`/transliterate`).
- *Spoken update for the parent:* model Bulbul v4 Flash. Call `client.text_to_speech.convert(text=..., language_code=..., model="bulbul:v4-flash", speaker=..., pace=0.8, dict_id=...)` (`/text-to-speech`). Up to 2,500 characters, native script.
- *Household assistant in the app:* streaming text to speech with `client.text_to_speech_streaming.connect(model="bulbul:v4-flash")` (`wss://api.sarvam.ai/text-to-speech/ws`), or `client.text_to_speech.convert_stream(...)` (`/text-to-speech/stream`).
  - The voice agent SDKs are Web `ConversationAgent` (`sarvam-conv-ai-sdk/browser`), React Native (`sarvam-conv-ai-sdk/react-native`), Flutter `SamvaadAgent` (`sarvamconv_ai_sdk`), and Python `AsyncSamvaadAgent` (`sarvam-conv-ai-sdk`) for server-side sessions.

**9. Handing over**
- *One doctor record (summary, last reports, current medicines, trend):* model Sarvam-105B with 128K context. Call `client.chat.completions(model="sarvam-105b", ...)` over the digitised reports and the household record.
- *Record in the doctor's or family's language:* Document Translation. Call `client.document_translation.create(...)`, `start(...)`, `get_live_status(...)`, `trigger_export(...)` and `get_export_status(...)` (`translate/document/jobs`). Up to 12 target languages per job, with layout preserved.

**10. Closing**
- *Dispensed quantity from the chemist receipt:* call `client.doc_ai.extract(...)` with a receipt schema (medicine, quantity dispensed, date, chemist). The quantity and its `confidence` and `sources` are stored as the provenance of the days-of-cover figure.
- *Next refill date:* set in the product backend from the dispensed quantity. The next campaign cohort picks it up.
- *Who did what:* the on-end hook (agent configuration), the campaign or instant-outbound webhook payloads, and `GET .../transcripts/{interaction_id}`.

**Across all stages**
- *Refusal and escalation tests:* `POST https://apps.sarvam.ai/api/evals/v1/{org_id}/{workspace_id}/test-suites/{test_suite_id}/runs`.
- *Audit trail:* Agent Analytics (the attempts, interactions, transcripts and recordings endpoints under `/api/analytics/v1/`) and Boards.
- *Build-time help only, not in production:* the Sarvam MCP server.

---

Now write the complete `README.md`. Output only the Markdown file content, starting with `# Family Health Agent`.
