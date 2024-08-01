from litellm import completion
import sys,time
from fgsutils import read_file, PurifyInput

class LocalLM( ):
    def __init__( self, modelnm='mistral-nemo'): #gemma2:9b'):
        self.sysmsg = "使用者會輸入中文詞, 請造句, 不需解釋"

        aa="""使用者會輸入中文句子, 請協助判斷其屬於為句子或單詞. 以下列 JSON 格式回應, 不需解釋.

input:
        海峽兩岸
output:
        {
            "text":"海峽兩岸",
            "type":"單詞"
        }
"""
        self.model_name = modelnm
    def ask( self, userprompt):
        msgs = [ 
                { 'role':'system', 'content': self.sysmsg},
                { 'role':'user', 'content': userprompt}
        ]
        response = completion(
            model=f'ollama/{self.model_name}',
            messages=msgs, 
            api_base="http://localhost:11434",
            #format = "json"
            #stream=True
        )
        return response
    def showresponse( self):
        print(response) # response is a generator
        for chunk in response:
            delta = chunk['choices'][0]['delta']
            print( delta.content, end="", flush=True)
            #time.sleep(0.1)
        print('')

def main():
    lm = LocalLM()
    lines = read_file( sys.argv[1])
    a = PurifyInput(lines)
    inputs = a.load()
    for inp in inputs[50:80]:
        print(inp[0])
        res = lm.ask(inp[0] )
        print(res.choices[0].message.content)
if __name__ == "__main__":
    main()
