from dotenv import load_dotenv
from openai import AsyncOpenAI
import chainlit as cl

load_dotenv()
client = AsyncOpenAI()

# Instrument the OpenAI client
cl.instrument_openai()

settings = {
    "model": 'ft:gpt-4o-2024-08-06:ipevo-corp:20241226:Aia7iefG',
    #"model": "ft:gpt-4o-mini-2024-07-18:ipevo-corp::9qI6ek8y",
    #"model": 'ft:gpt-4o-mini-2024-07-18:ipevo-corp:fgs-glossary3:9ssy45aS',
    #"model": 'ft:gpt-4o-mini-2024-07-18:ipevo-corp:fgs-glossary3:9srFRIKs',
    "temperature": 0,
}

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="佛光山專屬名詞",
            message="在最新一期的佛光世紀中，有一篇文章詳細介紹了禪修的諸多好處。",
            ),

        cl.Starter(
            label="佛經討論",
            message="師父向弟子解釋了真空妙有的深意，並勸勉他們日常生活中體驗這一真理。",
            ),
        cl.Starter(
            label="生活哲理",
            message="佛教經典中常說，有相皆虛妄，無我即菩提，提醒我們不要執著於表面的現象。",
            ),
        cl.Starter(
            label="佛經討論2",
            message="星雲說偈乃是佛教禪宗詩偈的詮釋，讓人們從詩中體會佛法的智慧。",
            )
        ]

@cl.on_chat_start
async def start():
    settings = await cl.ChatSettings(
        [
            TextInput(id="AgentName", label="Agent Name", initial="AI"),
        ]
    ).send()
    value = settings["AgentName"]

@cl.on_chat_start
async def start():
    elements = [
        cl.File(
            name="hb_glossary_v2_utf8.txt",
            path="./hb_glossary_v2_utf8.txt",
        ),
    ]
    await cl.Message(
        content="This message has a file element", elements=elements
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    response = await client.chat.completions.create(
        messages=[
            {
                "content": "你是一個佛學專家,精通中英文佛教詞彙,會將輸入中文翻譯為英文",
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

