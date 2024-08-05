import sys
import json

def prettyprint( cap, dic):
    print( cap, json.dumps( dic, sort_keys=True, indent=4))

class FilterDataset:
    def __init__(self, fn):
        self.fixed_entries= []
        self.entries = []
        self.stats={ 'normal':0, 'malform':0, 'multi':0, 'multi2':0, 'invalid_multi':0, 'no_en':0, 'invalid_phrase':0, 'invalid_tr':0, 'extra_tr_key':0, 'zh_val_dict':0, 'en_val_dict':0, 'extra_list':0, 'inconsist_en':0, 'others':0 }
        self.load_dataset(fn)
    def sprettyprint(self, etype, dic):
        self.stats[etype]+=1
        if self.stats[etype]==1:
            prettyprint( etype, dic)
    def fix_multi( self, tr):
        spp = int( len(tr['sentences']) / len(tr['phrases']) )
        for i, phrase in enumerate(tr['phrases']):
            bi = i*spp
            e = { 'phrase': phrase, 'sentences': tr['sentences'][bi:bi+spp]}
            self.fixed_entries.append({ 'translation':e})
    def invalid_tr_keys( self, tr):
        valid_keys = ['phrase', 'phrases', 'sentences']
        invalid_keys=[]
        for key in tr.keys():
            if not key in valid_keys:
                invalid_keys.append(key)
        return invalid_keys
    def check_schema(self, fgse):
        if not 'translation' in fgse:
            print('no translation field?')
        etype = 'others'
        tr = fgse['translation']
        if isinstance( tr, list):
            """ {
            "translation": [{"phrase": {"zh": "新生活七誡運動"...}, "sentences":[] ]
            }
            """
            etype = 'extra_list'
            self.fixed_entries.append({ 'translation':tr[0]})
        elif 'phrase' in tr:
            etype = 'normal'
            phrase = tr['phrase']
            if isinstance( phrase, str):
                print('found phrase is string')
                """
                { "phrase": "心甘情願", "sentences": [{"zh": "儘管困難重重，他仍心甘情願地承擔起重任。", "en": "Despite the numerous challenges, he was perfectly willing to take on the heavy responsibilities."}]
                """
                etype = 'invalid_phrase'
                tr['phrase'] = { 'zh':phrase, 'en':''}
                self.fixed_entries.append( { 'translation':tr})
            elif isinstance( phrase, list):
                etype = 'multi'
                tr['phrases'] = phrase
                self.fix_multi( tr)
            elif 'sub_phrases' in tr:
                etype = 'invalid_tr'
            elif len( self.invalid_tr_keys(tr))>0:
                etype = 'extra_tr_key'
                invkeys = self.invalid_tr_keys(tr)
                #print('invkeys=', invkeys)
                for k in invkeys:
                    del tr[k]
                self.fixed_entries.append( {'translation':tr})
            elif not ('en' in phrase):
                """
                {'phrase': {'zh': '德國佛教傳道會', 'en1': 'Buddhistischen Missionsverein fur Deutschland', 'en2': 'Buddhist Missionary Association of Germany'},
                """
                etype = 'no_en'
            elif isinstance( phrase['en'], dict):
                """
                "phrase": {
                    "zh": "色塵:sight",
                    "en": {"sight": "色塵", "sound": "聲塵", "smell": "香塵", "taste": "味塵", "touch": "觸塵", "dharmas": "法塵"}
                }
                """
                etype = 'en_val_dict'
            elif isinstance( phrase['zh'], dict):
                """
                "phrase": {
                    "zh": {"佛光人的精神": "常住第一、自己第二; 大眾第一、自己第二; 信徒第一、自己第二; 佛教第一、自己第二"}
                """
                etype = 'zh_val_dict'
                (k,v) = list(phrase['zh'].items())[0]
                phrase['zh'] =  f'{k}:{v}'
                self.fixed_entries.append({ 'translation':tr})

            elif isinstance( phrase['zh'], str) and isinstance( phrase['en'], list):
                """ example entry
                { "phrase": {"zh": "主任委員", "en": ["Executive Director", "Committee Director (BLIA)"]}
                """
                etype = 'inconsist_en'
            elif isinstance( phrase['zh'], list):
                """ example entry: so ugly!!
                "phrase": {
                    "zh": ["一個真誠的微笑 給人無限的歡喜", "一句適當的鼓勵 給人無窮的受用", "一件慈悲的善行 給人無量的因緣", "一則應機的故事 給人無盡的啟示"], 
                    "en": ["A sincere smile offers immeasurable joy.", "A fitting encouragement offers endless support.", "An act of compassion offers boundless possibilities.", "A relevant story offers infinite inspirations."]
                }
                """
                etype = 'multi2'
                phrases=[ { 'zh':zh, 'en':phrase['en'][i] } for i,zh in enumerate(phrase['zh'])]
                self.fix_multi( { 'phrases': phrases, 'sentences': tr['sentences']})

        elif 'phrases' in tr and 'sentences' in tr:
            phrases = tr['phrases']
            if isinstance( phrases, dict):
                """
                {"phrases": {"心甘情願": "Perfectly Willing", "永往直前": "Forge Bravely Ahead"},
                """
                etype = 'invalid_multi'
                nphrases=[]
                for k,v in phrases.items():
                    nphrases.append( {'zh':k, 'en':v})
                tr['phrases'] = nphrases
            else:
                #print( f"{len(tr['phrases'])} phrases and {len(tr['sentences'])} sentences")
                etype = 'multi'
            self.fix_multi( tr)
        self.sprettyprint( etype, tr)
        return etype == 'normal'
    def load_dataset( self, infn):
        with open( infn, 'r', encoding='utf-8') as f:  #load JSONL
            idx=0
            for line in f:
                fgse = json.loads(line)
                valid = self.check_schema(fgse)
                if valid:
                    self.entries.append(fgse)

    def show_fixed( self):
        for i,e in enumerate(self.fixed_entries):
            print(i, e)
    def show_stats(self):
        print(self.stats)
        print('number of fixed entries:', len(self.fixed_entries))
    def save_dataset(self, outfn):
        with open(outfn, 'w', encoding='utf-8') as f:
            #TODO: via itertools.chain() would be more elegant
            for e in self.entries:
                f.write(json.dumps(e, ensure_ascii=False)+ "\n")
            for e in self.fixed_entries:
                f.write(json.dumps(e, ensure_ascii=False)+ "\n")
 
fd = FilterDataset( sys.argv[1])
fd.show_stats()
dstfn= 'fixed_fgs.jsonl'
fd.save_dataset( dstfn)
print( f'{dstfn} saved')


