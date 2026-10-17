# Deploying the Family Health Agent backend

## Why not GitHub Pages

GitHub Pages serves static files. It runs no server-side process, so it cannot
host a FastAPI app, and it has nowhere to keep a secret. Putting the backend on
Pages would mean calling `api.sarvam.ai` from browser JavaScript with
`SARVAM_API_KEY` embedded in the page — which publishes a live key to anyone who
opens devtools, and breaks the rule that the key is read server-side only
(`app/config.py` is the single place it is read).

Pages is still the right home for a **landing or docs page**. It is not an option
for the API.

The same objection rules out any purely static host (Netlify drop, S3 website,
Cloudflare Pages without Workers).

## What this backend actually needs

| Need | Why |
|---|---|
| A long-running Python process | Saaras batch jobs and the clinic-call dialogue span several seconds to minutes |
| Server-side environment variables | `SARVAM_API_KEY`, and the three Indus vars for a real outbound call |
| A writable directory | Bulbul output is decoded to WAV under `out/` |
| Outbound HTTPS | `api.sarvam.ai` and `apps.sarvam.ai` |
| No inbound public callback (yet) | Hooks and webhooks arrive only once the Indus agents are deployed |

Nothing here needs a GPU, a queue or a database in this build: the store is
in-memory and seeded from `fixtures/`.

## Recommended: Render (free web service)

Best fit because it deploys straight from the GitHub repo with no local Docker,
injects secrets as dashboard env vars, and gives a stable HTTPS URL.

1. Push this repo to GitHub (done by the repo's git history).
2. Render dashboard → **New → Blueprint** → select the repo. `render.yaml` at the
   root is picked up automatically.
3. Set `SARVAM_API_KEY` in the dashboard when prompted (it is `sync: false`, so it
   is never read from the repo).
4. Wait for the first deploy, then check `https://<service>.onrender.com/healthz`.

Caveat on the free plan: the service sleeps after inactivity, so the first request
after a sleep takes ~30-50 s to wake. That matters for a live demo — hit
`/healthz` a minute beforehand.

## Alternative: Hugging Face Spaces (Docker SDK)

Good if the audience is an AI-demo audience, and it does not sleep as
aggressively. Create a Space with the **Docker** SDK, push this repo to the Space
remote, and add `SARVAM_API_KEY` under Settings → Secrets. The root `Dockerfile`
already listens on 7860, which is what Spaces expects.

Note that a public Space exposes the API to anyone. Keep the Space private, or
put an auth header in front of the routes first.

## Alternative: Google Cloud Run

The best technical fit — scales to zero, no sleep penalty on a warm instance,
60-minute request ceiling that suits long calls. It costs more setup: a GCP
project, billing, `gcloud` installed, and Secret Manager for the key. Worth it for
anything beyond a demo, overkill for one.

```
gcloud run deploy family-health-agent --source . --region asia-south1 \
  --set-secrets SARVAM_API_KEY=sarvam-api-key:latest --allow-unauthenticated
```

## Not suitable

- **Vercel / Netlify Functions**: the serverless timeout (10-60 s) cuts off Saaras
  batch jobs and the clinic-call dialogue, and the filesystem is read-only apart
  from `/tmp`.
- **GitHub Pages and other static hosts**: see above.

## Before any public deploy

The current build has **no authentication on its routes**, because every caller so
far has been a test or the local app. Anything with a public URL and a live
`SARVAM_API_KEY` behind it is a billable open relay for transcription and speech.
Put an API key header, or at minimum IP allow-listing, in front of the routers
before sharing a URL. This is deliberately left as an `# OPEN:` rather than
half-built.

Likewise, the in-memory store means every restart empties the household back to
the fixture. That is fine for a demo and wrong for anything else.
