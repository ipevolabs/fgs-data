import json
import sys
from collections import defaultdict
from datasets import load_dataset

#finetune dataset validation code from OpenAI
class OpenAIFinetuneValidator:
    def load_jsonl(self, infn):
        with open( infn, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f]

    def valid_openai_ft(self, dataset):
        # Format error checks
        format_errors = defaultdict(int)
        for ex in dataset:
            if not isinstance(ex, dict):
                format_errors["data_type"] += 1
                continue
            messages = ex.get("messages", None)
            if not messages:
                format_errors["missing_messages_list"] += 1
                continue
            for message in messages:
                if "role" not in message or "content" not in message:
                    format_errors["message_missing_key"] += 1
                if any(k not in ("role", "content", "name", "function_call", "weight") for k in message):
                    format_errors["message_unrecognized_key"] += 1
                if message.get("role", None) not in ("system", "user", "assistant", "function"):
                    format_errors["unrecognized_role"] += 1
                content = message.get("content", None)
                function_call = message.get("function_call", None)
                if (not content and not function_call) or not isinstance(content, str):
                    format_errors["missing_content"] += 1
            if not any(message.get("role", None) == "assistant" for message in messages):
                format_errors["example_missing_assistant_message"] += 1
        if format_errors:
            print("Found errors:")
            for k, v in format_errors.items():
                print(f"{k}: {v}")
            return False
        return True
    def __init__(self, fn):
        self.entries = self.load_jsonl(fn)
    def valid( self):
        return self.valid_openai_ft(self.entries)
 
class FGSFinetuneProcessor:
    def __init__(self, fgsda_file):
        self.sysprompt = "你是一個佛學專家,精通中英文佛教詞彙,會將輸入中文翻譯為英文."
        trset = self.load_fgsda_file( fgsda_file)
        self.trset = trset
        
    def load_fgsda_file(self, fn):
        ds = load_dataset('json', data_files=fn, split='train')
        return ds.map( lambda x:x['translation'], remove_columns=ds.column_names)
        
    def hf_dataset_basics(self, ds):
        print('type:',type(ds))
        print('Columns:', ds.column_names)
        print("Features:", ds.features)
        print('Rows:', ds.num_rows)
        df = ds.to_pandas()
        print(df.head())
        
    def internal_verify(self, ds):
        zcount = ds.filter( lambda x:x['phrase']==None).num_rows
        print('number of empty entries:', zcount)

    def transform_for_finetune( self, batch):
        rets = []
        for i, phrase in enumerate(batch['phrase']):
            phrase['split']='train'
            rets.append(phrase | {'split':'train'})
            ## note: the concept of dataset is more like table.  It's kind of "column-first" so you don't do batch[i]['sentences'] 
            sentences = batch['sentences'][i]
            for si,sentence in enumerate(sentences):
                split = 'validation' if si == (len(sentences)-1) else 'train' 
                rets.append( sentence | {'split':split})
        return {'finetune':rets }
    
    #OpenAI conversational message format for finetune
    def transform_for_openai(self, ex):
        return {"messages":[
            {"role": "system", "content": self.sysprompt},  
            {"role": "user", "content": ex['finetune.zh']},
            {"role": "assistant", "content": ex['finetune.en']}
        ]}

    def outpathes( self, dstfn, splits):
        if len(splits)==1:
            return { splits[0]:f'{dstfn}.jsonl' }
        return {split: f'{dstfn}_{split}.jsonl' for split in splits}

    def export_openai_ftfile( self, outfn, with_validation=False):
        inds = self.trset
        ftset_all = inds.map( self.transform_for_finetune, batched=True, remove_columns=inds.column_names)
        fttab = { 'train': ftset_all }
        if with_validation:
            ftset_train = ftset_all.filter(lambda ex: ex['finetune']['split'] == 'train')
            ftset_validation = ftset_all.filter(lambda ex: ex['finetune']['split'] == 'validation')
            fttab = { 'train':ftset_train, 'validation':ftset_validation }
        dstfntab = self.outpathes( outfn, list(fttab.keys()))
        for split,ds in fttab.items():
            flatset = ds.flatten()
            transformed_dataset = flatset.map( self.transform_for_openai, remove_columns=flatset.column_names)
            dstpath = dstfntab[split]
            transformed_dataset.to_json( dstpath, orient='records', lines=True, force_ascii=False)
            ov = OpenAIFinetuneValidator( dstpath)
            print(f'Finetune dataset file {dstpath} saved. File is valid = {ov.valid()}')
    def export( self, outfn, filetype='openai', with_validation=False):
        if filetype != 'openai':
            print('file types other than openai are not supported yet.')
            return
        self.export_openai_ftfile( outfn, with_validation)
        
if __name__ == "__main__":
    infn= sys.argv[1]
    if len(sys.argv)<3:
        [bfn,efn] = infn.rsplit('.', 1)
        outfn = f'{bfn}_ft.{efn}'
    else:    
        outfn = sys.argv[2]
    
    fgsftp = FGSFinetuneProcessor(infn)
    outfn = outfn.rsplit('.', 1)[0]
    fgsftp.export( outfn)

