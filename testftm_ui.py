from dotenv import load_dotenv
from openai import AsyncOpenAI
import chainlit as cl

load_dotenv()
client = AsyncOpenAI()

# Instrument the OpenAI client
cl.instrument_openai()

settings = {
    "model": "ft:gpt-4o-mini-2024-07-18:ipevo-corp::9qI6ek8y",
    "temperature": 0,
}

@cl.on_message
async def on_message(message: cl.Message):
    response = await client.chat.completions.create(
        messages=[
            {
                "content": "你是一個佛學專家,精通各種佛教中英文詞彙,你總是將使用者輸入翻譯成英文",
                "role": "system"
            },
            {
                "content": message.content,
                "role": "user"
            }
        ],
        **settings
    )
    await cl.Message(content=response.choices[0].message.content).send()

