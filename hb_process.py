import sys
import argparse
from glossary_augumentation import phrases_to_sentences,append_jsonl

def read_utf8_file_to_list(file_path):
    try:  
        with open(file_path, 'r', encoding='utf-8') as file:  
            lines = file.readlines()  
        # Strip newline characters from the end of each line  
        lines = [line.strip() for line in lines]  
        return lines  
    except FileNotFoundError:  
        print(f"Error: File not found: {file_path}")  
        return []  
    except Exception as e:  
        print(f"An error occurred: {e}")  
        return []  

class PurifyInput:
    def __init__(self, lines):
        self.long_entry_cnt=0
        self.lines = lines

    def check_entry( self, entry):
        sub_entries=[]
        if len(entry['zh'])>30:
            #print(entry)
            self.long_entry_cnt+=1
        #if  '?' in entry['zh']:
        #    print( f'{zh} --> {en}')

    def load( self):
        entries=[]
        for line in self.lines:
            line = line.strip(', ')
            toks=line.split(',',1)
            if len(toks)!=2:
                print('not parsable ', line)
                continue
            [zh,en] = toks
            if zh.lower()=='removed':
                continue
            zh = zh.strip('\'"')
            en = en.strip('\'"')
            entry = [ zh, en] #{ 'zh':zh, 'en':en}
            #self.check_entry(entry)
            entries.append( entry)
        self.entries = entries
        print(f'{len(entries)} entries.  {self.long_entry_cnt} long entries')
        return self.entries

    def save( self, file_path:str, sep='\t'):
        with open(file_path, 'w') as file:
            for entry in self.entries:
                file.write(f"{entry[0]}{sep}{entry[1]}\n")

def getargs():
    parser = argparse.ArgumentParser(description="Generating full sentences from a FGS Buddhism glossary file.")
    parser.add_argument('file_path', type=str, help='File path of the original line-based glossary file.')
    parser.add_argument('--endidx', type=int, default=None, help='End of line NO to process. Default is the end of file')
    parser.add_argument('--skip', type=int, default=0, help='Number of lines to skip.  Default: no skip')
    parser.add_argument('--model', type=str, default='gpt-4o-mini', help='The OpenAI model.  Default: gpt-4o-mini')
    parser.add_argument('--nsentences', type=int, default=2, help='Number of example sentences to generate per entry. Default: 4')
    parser.add_argument('--outfile', type=str, default='auglossary.jsonl', help='Output file path')
    return parser.parse_args()

def errlog(text):
    file_path = 'errdalog.txt'
    with open(file_path, 'a') as file:
        file.write( text + '\n')

from typing import List,Dict
import pandas as pd

def load_glossary_old( file_path:str)->List[str]:
    lines = read_utf8_file_to_list( file_path)
    a = PurifyInput(lines)
    return a.load()

def load_glossary( file_path:str)->List[str]:
    df = pd.read_csv( file_path, sep='\t')
    return df.values.tolist()

def main():
    args = getargs()
    #inputs = load_glossary_old( args.file_path)
    inputs = load_glossary( args.file_path)
    print(f'Line range {args.skip} to {args.endidx}')
    auggen= phrases_to_sentences(
        phrase_pairs = inputs[args.skip:args.endidx],
        model = args.model,
        noutputs = args.nsentences)
    idx=args.skip
    for resp in auggen:
        print(f'{idx}: {inputs[idx]}')
        try:
            append_jsonl( args.outfile, resp)
        except Exception as e:
            errlog( ','.join(inputs[idx]) +':'+ str(e))
        idx+=1
if __name__ == "__main__":
    main()
