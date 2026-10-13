import os

import httpx
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    StopResponse,
    cli,
    inference,
    llm,
)
from livekit.plugins import synthesia

load_dotenv(".env.local")

# 127.0.0.1 use kiya hai taaki localhost/IPv6 ka confusion na ho
SPRING_AVATAR_URL = os.getenv(
    "SPRING_AVATAR_URL", "http://127.0.0.1:8080/api/avatar/ask"
)

# FAKE_BRAIN=1 ho to Spring ke bina test hoga: avatar bas wahi dohrayega jo aapne bola.
FAKE_BRAIN = os.getenv("FAKE_BRAIN") == "1"

# Spring Boot ho to .env.local me USE_SPRING=1 daalo. Warna avatar khud (LiveKit Inference LLM) jawab dega.
USE_SPRING = os.getenv("USE_SPRING") == "1"

BUILTIN_INSTRUCTIONS = (
    "Tum Coder Army ke AI avatar ho, ek dostana teacher jo programming aur coding "
    "sikhata hai. User ki baat ka jawab Hindi me do (Devanagari script), aasan "
    "bhasha me. Jawab chhote rakho, 2-3 vaakya, kyunki ye voice conversation hai. "
    "Markdown, list ya emoji bilkul mat use karo."
)

AVATAR_ID = os.environ["SYNTHESIA_AVATAR_ID"]
# LiveKit Inference ke default Cartesia voices hi chalte hain (custom voices nahi).
# Alag awaaz chahiye to .env.local me TTS_VOICE=<Cartesia library ka voice id> daalo.
TTS_MODEL = os.getenv("TTS_MODEL", "cartesia/sonic-3")
TTS_VOICE = os.getenv("TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "hi")

CARTESIA_VOICE_ID = os.getenv("CARTESIA_VOICE_ID")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")


def build_tts():
    """Aapki custom Cartesia voice (CARTESIA_API_KEY ke saath) ya LiveKit Inference ki default voice."""
    if CARTESIA_API_KEY and CARTESIA_VOICE_ID:
        from livekit.plugins import cartesia

        print("TTS: Cartesia plugin, custom voice", CARTESIA_VOICE_ID)
        return cartesia.TTS(
            model="sonic-3",
            voice=CARTESIA_VOICE_ID,
            language=TTS_LANGUAGE,
            api_key=CARTESIA_API_KEY,
        )

    print("TTS: LiveKit Inference default voice", TTS_VOICE)
    return inference.TTS(model=TTS_MODEL, voice=TTS_VOICE, language=TTS_LANGUAGE)


server = AgentServer()


async def ask_spring(question: str) -> str:
    """Spring Boot 'brain' se answer lo."""
    if FAKE_BRAIN:
        return f"Aapne kaha: {question}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            SPRING_AVATAR_URL,
            json={"question": question},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["answer"]


class SpringBrainAgent(Agent):
    """Har user turn complete hone ke BAAD Spring ko call karta hai aur answer bolta hai."""

    def __init__(self):
        super().__init__(
            instructions=(
                "You are the realtime voice adapter for the Coder Army AI avatar. "
                "Do not generate answers yourself. The Spring Boot service is "
                "responsible for all AI reasoning and knowledge."
                if (USE_SPRING or FAKE_BRAIN)
                else BUILTIN_INSTRUCTIONS
            )
        )

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        # Built-in mode: normal LLM reply chalne do (Spring/echo skip)
        if not (USE_SPRING or FAKE_BRAIN):
            return

        question = (new_message.text_content or "").strip()
        if not question:
            raise StopResponse()

        print("USER:", question)

        try:
            answer = await ask_spring(question)
            print("SPRING:", answer)
        except Exception as error:
            print(f"ERROR calling Spring ({SPRING_AVATAR_URL}): {type(error).__name__}: {error}")
            answer = "Sorry, abhi answer generate karne me problem aa rahi hai."

        self.session.say(answer, allow_interruptions=True)

        # LLM se auto-reply mat banao, jawab Spring ka hi bolna hai
        raise StopResponse()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="multi"),
        # llm sirf pipeline ke liye hai; StopResponse ki wajah se ye kabhi answer nahi banata
        llm=inference.LLM(model="openai/gpt-4.1-mini"),
        tts=build_tts(),
    )

    print("SYNTHESIA AVATAR ID:", AVATAR_ID)
    if FAKE_BRAIN:
        print("BRAIN: FAKE (echo)")
    elif USE_SPRING:
        print("BRAIN: Spring ->", SPRING_AVATAR_URL)
    else:
        print("BRAIN: built-in LLM (LiveKit Inference)")

    try:
        avatar = synthesia.AvatarSession(
            synthesia.AvatarConfig(avatar_ids=[AVATAR_ID])
        )
        await avatar.start(session, room=ctx.room)
    except Exception as e:
        print("AVATAR FAILED, voice-only chalega:", e)

    await session.start(agent=SpringBrainAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)