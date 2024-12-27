from dotenv import load_dotenv
from openai import AsyncOpenAI
import chainlit as cl
from chainlit.input_widget import TextInput
import os
import json
from typing import List,Dict

warnings.filterwarnings('ignore')
load_dotenv()
#print('OpenAI API Key:', os.getenv('OPENAI_API_KEY'))
client = AsyncOpenAI()

# Instrument the OpenAI client
cl.instrument_openai()

settings = {
    "model": 'ft:gpt-4o-2024-08-06:ipevo-corp:20241226:Aia7iefG',
    #"model": "ft:gpt-4o-mini-2024-07-18:ipevo-corp::9qI6ek8y",
    #"model": 'ft:gpt-4o-mini-2024-07-18:ipevo-corp:fgs-glossary3:9ssy45aS',
    #"model": 'ft:gpt-4o-mini-2024-07-18:ipevo-corp:fgs-glossary3:9srFRIKs',
    "temperature": 0
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


initial_sysprompt = """
You are an assistant specializing in Buddhist studies, with expertise in translating Buddhist talks from Chinese to English. Your main role is to deliver real-time translations that are accurate and contextually appropriate.

Core Translation Rules:
- Maintain consistency with previously translated segments
- Honor the specialized vocabulary provided in the context
- Provide natural, fluent translations that work in context
- Handle both complete and partial sentences appropriately
- Never explain or comment on the translation unless explicitly asked
- Output the translation in the JSON format 

Expected Input JSON Format:  
{  
    "context": {  
        "previous_segments": [
            {  
                "source": "source text",
                "translation": "translated text"
            }
        ],
        "specialized_terms": {
            "term1": "translation1",
            "term2": "translation2"
        }
    },
    "input":  "text to translate"
}

Output JSON Format:
{
    "output": "translation of input text"
}

JSON Processing Rules:
- Use all previous segments in the context for maintaining consistency
- Apply specialized terms exactly as provided in the JSON
- If a specialized term has metadata, use the "translation" field
- Process the input text directly from the "input" field or "input.text" if in object format  


Example Input and Output:  
Input:
```json
{  
    "context": {  
        "previous_segments": [  
            {  
                "source": "我們知道有一部藏經叫做鐵眼藏經, 來源是日本鐵眼禪師",
                "translation": "We know of a canon called the Tetsugan Canon, originating from Japanese Tetsugan Zen Master.",
            }  
        ],
        "specialized_terms": {
            "愛比科技": "IPEVO"
        }
    },
    "input":"鐵眼禪師為宣傳佛法，募款印刷大藏經救助眾生"
}
```

Output:
```json
{
    "output": "To promote Buddhism, Tetsugan Zen Master raised funds to print the Great Canon to save sentient beings"
}
```

"""

promptSettings = {}
previous_segments = []
systemPrompt = ""
specializedTerms = {}
initial_terms = {
    "愛比科技": "IPEVO Corp",
    "松下電器": "Panasonic",
    "金池長老": "monk Jinchi",
    "西遊記": "The Journey to The West",
    "唐僧": "Tang Priest",
    "鐵拳": "Tekken",
    "正念": "mindfulness",
    "大念處經":"The Discourse on the Establishing of Mindfulness"
}

@cl.on_chat_start
async def start():
    psettings = await cl.ChatSettings(
        [
            TextInput(
                id="SpecializedTerms",
                label="Specialized Terms",
                initial=json.dumps(initial_terms, ensure_ascii=False, indent=2),
                multiline=True,
            ),
            TextInput(
                id="SystemPrompt",
                label="System Prompt",
                initial=initial_sysprompt,
                description="Enter the system prompt to define the AI assistant's behavior",
                multiline=True
            ),
        ]
    ).send()
    promptSettings.update(psettings)
    previous_segments = []

@cl.on_settings_update
async def on_settings_update(settings: Dict):
    print('settings updated:', settings)
    promptSettings.update(settings)


def wrap_user_message(umsg:str)->str:
    jterms = promptSettings['SpecializedTerms'] 
    wrapped_msg = {
        "context": {
            "previous_segments": previous_segments,
            "specialized_terms": json.loads(jterms)
        },
        "input": umsg,
    }
    #print("Wrapped Message:", wrapped_msg)
    # encode wrapped_msg to json
    return json.dumps(wrapped_msg)

@cl.on_message
async def on_message(message: cl.Message):
    system_prompt = promptSettings["SystemPrompt"]
    input_text = message.content
    response = await client.chat.completions.create(
        messages=[
            {
                "content": system_prompt,
                "role": "system"
            },
            {
                "content": wrap_user_message(input_text),
                "role": "user"
            }
        ],
        **settings
    )
    print( 'response is ', response.choices[0].message)
    translated = response.choices[0].message.content
    tpair = { "source": input_text, "translation": translated}
    
    previous_segments.append(tpair)
    if len(previous_segments) > 5:
        previous_segments.pop(0)
    await cl.Message(translated).send()

