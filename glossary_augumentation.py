import os
import json
from dotenv import load_dotenv
from litellm import completion
from langfuse.decorators import langfuse_context, observe

load_dotenv()

def handle_response1(response):
    print(response.choices[0].message.content)
    # Check the token usage
    token_usage = response['usage']
    print(token_usage)

def format_response(response):
    ctn = json.loads( response.choices[0].message.content)
    #'completion_tokens'
    #'prompt_tokens'
    #total_tokens=316
    return { 'token_usage': dict(response['usage']), 'translation': ctn }

def phrases_to_sentences(inputs):
    model='gpt-4o-mini'
@observe()
def llm_completion( model, messages):
    return completion(model=model, messages=messages)

    sysmsg = [
        {"role": "system", "content": """
你是一個佛學專家, 精通中英文佛教詞彙, 使用者會提供一個佛教詞彙中英翻譯對, 請將其擴展成完整例句, 中文部分使用繁體中文, 以 JSON 輸出.
    
    JSON 輸出入範例:

    input:
        一心不二 -> Single-Heartedly
    output:
        {
            "phrase": { "zh": "一心不二", "en": "Single-Heartedly"},
            "sentences": [
                {
                    "zh":"她一心不二地投身於這個慈善項目，投入了無數的時間和不懈的努力。"
                    "en": "She single-heartedly dedicated herself to the charity project, putting in countless hours of hard work and unwavering commitment."
                }
            ]
        }
"""}
    ]
    for e in inputs:
        msgs = [ *sysmsg, { "role": "user", "content": f'{e[0]} -> {e[1]}'}]
        response = llm_completion(model=model, messages=msgs)
        yield response

def append_jsonl( jsonlfn, e):
    # Open the JSONL file in append mode  
    with open( jsonlfn, 'a') as file:
        rdict = format_response(e)
        file.write(json.dumps( rdict) + '\n')

if __name__ == "__main__": 
    inputs=[
        ['一以貫之', 'Be Consistent'],
        ['一心二門; 1. 心真如門 2. 心生滅門', 'One Mind Opens Two Doors: 1. The door of suchness; 2. The door of arising and ceasing' ],
        ['一心似月無圓缺 萬事如雲任去來',"A mind like the perfect full moon; Coursing through the world's troubles like free clouds."]
    ]
    auggen= phrases_to_sentences(inputs)
    for e in auggen:
        append_jsonl( 'test.jsonl', e)

