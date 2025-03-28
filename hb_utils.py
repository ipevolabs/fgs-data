import sys
from typing import List,Dict
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_glossary( file_path:str)->List[str]:
	df = pd.read_csv( file_path, sep='\t')
	adf = df[ ['#Chinese','#English']]
	return adf.values.tolist()

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

def main_listdup( shortgl:str, longgl:str):
	short_glossary = load_glossary( shortgl)
	long_glossary = load_glossary( longgl)
	# check if any of short glossary's Chinese entries are in long glossary Chinese entries
	dups = {}
	for sentry in short_glossary:
		[shortzh,shorten] = sentry
		for lentry in long_glossary:
			[longzh,longen] = lentry
			if shortzh in longzh:
				if shortzh not in dups:
					dups[shortzh] = { 'sentry': sentry, 'lentries':[]}
				if not shorten in longen: #only add those entries that are not exactly the same
					dups[shortzh]['lentries'].append( lentry)
	# pretty print the dups dictionary
	for (key,dup) in dups.items():
		if len(dup['lentries'])==0:
			continue
		print(dup['sentry'])
		for lentry in dup['lentries']:
			print(f'\t{lentry}')

def transform_entry( entry:tuple[str]) -> tuple[str]|None:
	chstr, enstr = entry
	to_remove = [ '顧問', '代表', '秘書', '理事']
	if chstr in to_remove:
		return ('','')
	ret = None 	
	# entries to transform
	if chstr == '國際佛光會　　分會':
		ret = ('國際佛光會洛杉磯分會', 'BLIA Los Angeles SubChapter')
	elif chstr == '國際佛光會　　協會':
		ret = ('國際佛光會洛杉磯協會', 'BLIA Los Angeles Chapter')
	elif chstr== '副會長':
		ret = ('副會長','Vice President')
	elif chstr == '國際佛光會世界總會　　辦事處':
		ret = '國際佛光會世界總會亞洲辦事處', 'BLIA World Headquarters Asia Regional Office'
	return ret

def main_adjust_multiple(  fns:List[str]):
	selcols = ['#Chinese','#English']
	merged_df = pd.read_csv(  fns[0], sep='\t')
	for fn in fns[1:]:
		dfnext = pd.read_csv( fn, sep='\t')
		merged_df = pd.concat([merged_df[selcols], dfnext[selcols]], ignore_index=True)

	#logger.debug( f'number of total rows : { len(merged_df)}')
	# Sort the DataFrame by columen '#Chinese'
	merged_df = merged_df.sort_values(by=['#Chinese'])
	# strip out quotes and remove newline characters
	quotechars = '\"\''
	merged_df['#Chinese'] = merged_df['#Chinese'].str.strip(quotechars)
	merged_df['#English'] = merged_df['#English'].str.strip(quotechars)

	# remove duplicates
	merged_df = merged_df.drop_duplicates(subset=['#Chinese'], keep='first')
	for idx,entry in merged_df.iterrows():
		transformed = transform_entry( (entry['#Chinese'], entry['#English']))
		if transformed:
			#print('transformed=', transformed, 'idx=', idx)
			if transformed[0] == '':
				merged_df.drop(idx, inplace=True)
				continue
			# update the entry
			merged_df.loc[idx, ['#Chinese', '#English']] = transformed
	#logger.debug( f'number of rows after adjusting: { len(merged_df)}')
	#output the tsv file to stdout
	print(merged_df.to_csv(sep='\t', index=False))

import json
def dump_ft_json( ftjson_fn:str):
	df = pd.read_json( ftjson_fn, lines=True)
	print('#Chinese\t#English\t#Sentences')
	#get the translation column as a new dataframe
	for index, row in df.iterrows():
        # Get the specified column
		tdict = row['translation']
		phrase = tdict['phrase']
		print(f"{phrase['zh']}\t{phrase['en']}")
		sentences = tdict['sentences']
		for sentence in sentences:
			print( f' \t \t{sentence["zh"]}')
			print( f' \t \t{sentence["en"]}')
		#print('')
	#df['translation']
	#"translation": {"phrase": {"zh": "七誡運動歌", "en": "Song of Encouragement"}, "sentences": [{"z"
	
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
	elif cmd=='listdup':
		main_listdup(*args)
	elif cmd=='adjust':
		main_adjust_multiple(args)
	elif cmd=='dumpftjson':
		dump_ft_json(*args)