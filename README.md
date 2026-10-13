# 🎓 Voice AI Avatar (LiveKit + Synthesia)

A real-time, voice-only AI avatar you can talk to from the browser. You speak, the avatar listens, thinks and answers back out loud with a lip-synced video avatar, in a full-screen UI with no typing.

## How it works

```
Browser (index.html)  ──token──►  Flask token server (server.py)
        │                                   │
        └────────── WebRTC ─────────────────┘
                         │
                   LiveKit Cloud room
                         │
              Python agent (agent.py)
        ┌────────────────┼────────────────────┐
   Speech-to-text    LLM "brain"         Text-to-speech
 (Deepgram Nova-3)  (LiveKit Inference  (Cartesia, custom
                     or your own API)      voice supported)
                         │
                Synthesia interactive avatar
                (joins the room, publishes video)
```

- **Frontend** (`index.html`): full-screen avatar video, one "start" button, mic mute and end-call buttons.
- **Token server** (`server.py`): a tiny Flask app that serves the page and issues short-lived LiveKit access tokens. Your LiveKit secret never reaches the browser.
- **Agent** (`agent.py`): a LiveKit Agents worker that handles speech-to-text, generates the answer, speaks it, and drives the Synthesia avatar.

## Features

- Voice-only conversation, full-screen avatar UI
- Hindi / Hinglish friendly (Deepgram `multi` language STT, Hindi TTS)
- Custom Cartesia voice support
- Three interchangeable "brains":
  1. **Built-in LLM** (default): answers via LiveKit Inference, no extra LLM key needed
  2. **External HTTP service** (e.g. Spring Boot): the agent forwards each question to your own API
  3. **Echo mode** (`FAKE_BRAIN=1`): repeats what you said, useful for testing the voice pipeline

## Requirements

- Python 3.11+
- A [LiveKit Cloud](https://livekit.io) project (URL, API key, API secret)
- A [Synthesia](https://www.synthesia.io) workspace with Interactive Avatar access (API key and an **Interactive ID** of an avatar your plan can use)
- Optional: a [Cartesia](https://cartesia.ai) account if you want your own custom voice

## Setup

```bash
git clone <your-repo-url>
cd <your-repo-folder>

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env.local
# now open .env.local and fill in your own values
```

### Environment variables

All configuration lives in `.env.local` (never committed). See `.env.example` for a template.

| Variable | Required | Description |
|---|---|---|
| `LIVEKIT_URL` | yes | Your LiveKit project URL, e.g. `wss://your-project.livekit.cloud` |
| `LIVEKIT_API_KEY` | yes | LiveKit API key |
| `LIVEKIT_API_SECRET` | yes | LiveKit API secret |
| `SYNTHESIA_API_KEY` | yes | Synthesia workspace API key |
| `SYNTHESIA_AVATAR_ID` | yes | Avatar **Interactive ID** (Avatars page, `•••` menu, *Copy Interactive ID*) |
| `CARTESIA_API_KEY` | no | Needed only for a custom Cartesia voice |
| `CARTESIA_VOICE_ID` | no | Your custom Cartesia voice ID (used together with `CARTESIA_API_KEY`) |
| `TTS_MODEL` | no | LiveKit Inference TTS model, default `cartesia/sonic-3` |
| `TTS_VOICE` | no | Default voice ID when no custom voice is set |
| `TTS_LANGUAGE` | no | TTS language, default `hi` |
| `USE_SPRING` | no | Set to `1` to forward questions to an external HTTP service |
| `SPRING_AVATAR_URL` | no | That service's URL, default `http://127.0.0.1:8080/api/avatar/ask` |
| `FAKE_BRAIN` | no | Set to `1` for echo mode |
| `AGENT_NAME` | no | Only if you use explicit agent dispatch |

## Run

Open two terminals (both with the virtual environment activated).

**Terminal 1: the agent**
```bash
python agent.py dev
```

**Terminal 2: the web server**
```bash
python server.py
```

Then open **http://localhost:8000**, click the start button, allow the microphone, and start talking.

> Use `localhost`, not your machine's IP address. Browsers only allow microphone access on `localhost` or HTTPS.

### Using an external HTTP "brain"

Set `USE_SPRING=1` and point `SPRING_AVATAR_URL` to your service. The agent sends:

```http
POST /api/avatar/ask
Content-Type: application/json

{ "question": "what the user said" }
```

and expects:

```json
{ "answer": "text the avatar should speak" }
```

### Testing the voice pipeline without any brain

```bash
FAKE_BRAIN=1 python agent.py dev
```

The avatar will repeat what you said.

## Customizing

- **Personality / language:** edit `BUILTIN_INSTRUCTIONS` in `agent.py`.
- **Voice:** set `CARTESIA_VOICE_ID` + `CARTESIA_API_KEY`, or change `TTS_VOICE`.
- **Look of the UI:** everything is in `index.html` (plain HTML/CSS/JS, no build step).

## Project structure

```
.
├── agent.py            # LiveKit agent: STT, answer generation, TTS, Synthesia avatar
├── server.py           # Flask server: serves the UI and issues LiveKit tokens
├── index.html          # Full-screen voice-only frontend
├── requirements.txt    # Python dependencies
├── .env.example        # Template for your secrets (copy to .env.local)
└── .gitignore
```

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Page connects but no avatar appears | Check the agent terminal. `SynthesiaError: ... avatarIds does not exist or is not accessible` means the ID is not an Interactive ID for your workspace or plan. `a Synthesia API key is required` means `SYNTHESIA_API_KEY` is missing. |
| Avatar joins but stays silent | TTS problem. Custom Cartesia voices need `CARTESIA_API_KEY`; LiveKit Inference only supports Cartesia's default voices. |
| Avatar says it cannot generate an answer | Only in external-brain mode: your HTTP service is not running or the URL is wrong. |
| Microphone does not work | Open `http://localhost:8000`, not an IP address, and allow mic access. |
| `KeyError: 'LIVEKIT_URL'` on `server.py` | `.env.local` is missing or in the wrong folder. It must sit next to `server.py`. |

## Security notes

- Secrets are loaded from `.env.local`, which is git-ignored. **Never commit it.**
- If a key was ever committed or shared publicly, rotate it in the provider's dashboard.
- `server.py` runs Flask's development server. For a public deployment, put it behind a production WSGI server (e.g. gunicorn) and HTTPS, and consider adding authentication to `/token`.

## License

Add a license of your choice (for example MIT) before publishing.