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

def getargs():
    parser = argparse.ArgumentParser(description="Generating full sentences from a FGS Buddhism glossary file.")
    parser.add_argument('file_path', type=str, help='File path of the original line-based glossary file.')
    parser.add_argument('--endidx', type=int, default=None, help='End of line NO to process. Default is the end of file')
    parser.add_argument('--skip', type=int, default=0, help='Number of lines to skip.  Default: no skip')
    parser.add_argument('--model', type=str, default='gpt-4o-mini', help='The OpenAI model.  Default: gpt-4o-mini')
    parser.add_argument('--outfile', type=str, default='auglossary.jsonl', help='Output file path')
    return parser.parse_args()

def main():
    args = getargs()
    lines = read_utf8_file_to_list( args.file_path)
    a = PurifyInput(lines)
    inputs = a.load()

    print(f'Line range {args.skip} to {args.endidx}')
    auggen= phrases_to_sentences(inputs[args.skip:args.endidx], args.model)
    idx=args.skip
    for e in auggen:
        print(f'{idx}: {inputs[idx]}')
        append_jsonl( args.outfile, e)
        idx+=1
if __name__ == "__main__":
    main()
