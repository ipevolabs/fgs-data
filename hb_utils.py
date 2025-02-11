import sys
from typing import List,Dict
import pandas as pd

def load_glossary( file_path:str)->List[str]:
	df = pd.read_csv( file_path, sep='\t')
	return df.values.tolist()

def find_index_of_string( glossary:List, tofind:str)->List:
	indexes=[]
	for idx,entry in enumerate(glossary):
		if tofind in ','.join(entry):
			indexes.append(idx)
			#print(f'{idx}: {entry}')
	return indexes

def is_endof_entry( line:str)->bool:
	#check if this line has the pattern like "line \d column \d" 
	return 'line' in line and 'column' in line

def find_second_last_colon(text:str)->int:  
	last = text.rindex(':')
	if last== -1:
		return -1
	return text[:last].rindex(':')

def analyze_errlog( file_path:str)->List[Dict]:
	errs = []
	with open(file_path, 'r') as file:
		acculines=[]
		for line in file.readlines():
			if not is_endof_entry(line):
				acculines.append(line)
				continue
			# find the last second last occurence of ':' in the line variable
			delimpos = find_second_last_colon(line)	
			last_str = line[:delimpos]
			errmsg = line[delimpos+1:]
			entrystr = ''.join(acculines) + last_str
			acculines = []
			try:
				[zh,en] = entrystr.split(',',1)
			except Exception as e:
				print('error entrystr:', entrystr)
				continue
			errs.append( {
				'zh':zh.strip().replace('\n',' ').replace('　',' '),
				'en':en.strip().replace('\n',' '),
				'errmsg':errmsg.strip(),
			})
	return errs

def main_find(glfn:str, tofind:str):
	glossary = load_glossary(glfn)
	print('to find ', tofind)
	indexes = find_index_of_string( glossary, tofind)
	for idx in indexes:
		print(f'{idx}: {glossary[idx]}')

def main_check( glfn:str):
	glossary = load_glossary( glfn)
	print(len(glossary), ' entries')
	print('glossary[-1]:', glossary[-1])

def main_errlog( glfn:str):
	elist = analyze_errlog( glfn)
	#print(f'{len(elist)} errors found')
	print('#Chinese\t#English')
	for e in elist:
		print(f'{e["zh"]}\t{e["en"]}')

if __name__ == "__main__":
	if len(sys.argv)<3:
		print('Usage: python hb_utils.py <command> [file_path] [optional_args]')
		sys.exit(1)

	cmd = sys.argv[1]
	args = sys.argv[2:]
	if cmd=='find':
		main_find( *args)
	elif cmd=='check':
		main_check( *args)
	elif cmd=='errlog':
		main_errlog(*args)