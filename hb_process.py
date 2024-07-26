import sys

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

class TermReview:
    def __init__(self, lines):
        self.long_entry_cnt=0
        self.lines = lines

    def check_entry( self, entry):
        sub_entries=[]
        if len(entry['zh'])>30:
            print(entry)
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
            entry = { 'zh':zh, 'en':en}
            self.check_entry(entry)
            entries.append( entry)
        self.entries = entries
        print(f'{len(entries)} entries.  {self.long_entry_cnt} long entries')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python read_file_to_list.py <file_path>")
        sys.exit(0)
    infn = sys.argv[1]
    lines = read_utf8_file_to_list( infn)
    a = TermReview(lines)
    a.load() 
