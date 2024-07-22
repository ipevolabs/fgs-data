import docx
import sys
from simplify_docx import simplify
import utils

def parse_paragraph( parav):
    assert len(parav)==1, "length of 'paragraph' is not 1"
    parav0 = parav[0]['VALUE']
    print(parav0)

def parse_table( tablev):
    tvlen=len(tablev)
    if tvlen!=1:
        print( f"length of 'table' is not 1.  it's {tvlen}")
    if tvlen==0:
        return
    tablev0=tablev[0] 
    print(tablev0)


#{'TYPE': 'table-row', 'VALUE': [{'TYPE': 'table-cell', 'VALUE': [{'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '登鸛雀樓'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '◎唐‧王之渙（688~742）'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '白日依山盡，黃河入海流。'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '欲窮千里目，更上一層樓。'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '──選自《文苑英華》'}]}]}, {'TYPE': 'table-cell', 'VALUE': [{'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'Climbing the Crane Pagoda'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'Wang Zhihuan (688 - 742, Tang Dynasty)'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'English translation: Miao Guang'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'Behind the mountain range sets the white sun,'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'Into the ocean flows the Yellow River;'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'To overcome the limit of the clairvoyant eye,'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': 'Climb yet another layer up the pagoda.'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '── from Wenyuan Yinhua'}]}, {'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '(Blossoms and Flowers of the Literature Garden)'}]}]}]}

#it's supposed to be two strings
def table_to_strs(tablev):
    tvlen=len(tablev)
    if tvlen!=1:
        print( f"length of 'table' is not 1.  it's {tvlen}")
    if tvlen==0:
        return
    #it's supposed to be one row consist of two columns
    row0v = tablev[0]
    [zhcell,encell] = row0v['VALUE']

    zhstrs = paragraphs_to_str(zhcell['VALUE'])
    enstrs = paragraphs_to_str(encell['VALUE'])
    return [zhstrs,enstrs]

#{'TYPE': 'paragraph', 'VALUE': [{'TYPE': 'text', 'VALUE': '我要把過去的種種視為昨日已過，'}]}
def paragraph_to_str( parav):
    assert len(parav)==1, "length of 'paragraph' is not 1"
    kv = parav[0]
    if kv['TYPE'] != 'text': #, 'conent of paragraph is not in type TEXT'
        return ''
    return kv['VALUE']

def p2s( parav):
    return paragraph_to_str(parav)

def paragraphs_to_str( paras):
    lines=[]
    for para in paras:
        if para['TYPE'] != 'paragraph':
            continue
        lines.append( p2s( para['VALUE']))
    return '\n'.join(lines)

def make_dayquote( dayblks):
    print(f'make_dayquote have {len(dayblks)} blocks')
    idx = 0
    date_str = p2s(dayblks[idx]['VALUE'])         #1月21日January 21st
    month, day = utils.parse_date( date_str)
    idx += 1
    quotes=[]
    while idx < len(dayblks):
        infos=[]
        for blk in dayblks[idx:]:
            if blk['TYPE']=='paragraph':
                infos.append(p2s(blk['VALUE'])) #C_20140831_ZW_T_AfterManyAutumns_p208  (October Merit Times)
            else:
                break
        idx+=len(infos)
        if not (idx < len(dayblks)):
            break
        
        nextblk = dayblks[idx]
        idx+=1
        assert nextblk['TYPE'] == 'table', f"expect there is a table but get a {nextblk['TYPE']}"
        tablev = nextblk['VALUE']
        if len(tablev)==0:
            continue
        [ zh, en ] = table_to_strs( tablev)
        quote = {
            'infos': '\n'.join( infos), 
            'content': {
                'zh': zh,
                'en': en
            }
        }
        quotes.append(quote)
    dayquote = {
        'date': [month,day],
        'quotes': quotes
    }
    return dayquote

def is_paragraph_date(parav):
    s = p2s(parav)
    month, day = utils.parse_date( s)
    return month != 0

def parse_monthdoc( dd):
    assert dd['TYPE']=='document', "not begin with a 'document'"
    dv = dd['VALUE']
    assert len(dv)==1, "length of 'document' is not 1"
    dv0 = dv[0]
    assert dv0['TYPE']=='body', "the first element of 'document' is not a 'body'"
    bodyv = dv0['VALUE']
    print(f'{len(bodyv)} blocks')
    tmpblks=[]
    dayquotes=[]
    for idx, blk in enumerate(bodyv):
        #assert para['TYPE']=='paragraph'
        blkt = blk['TYPE']
        blkv = blk['VALUE']
        print(f'block {idx} is a {blkt}')
        if idx==0:  #block 0 is always indication of begin of a month
            continue
        if blkt=='paragraph':
            print( '\t', p2s( blkv))
            if is_paragraph_date(blkv):
                if len(tmpblks)>0:
                    dayquote = make_dayquote(tmpblks)
                    dayquotes.append(dayquote)
                    tmpblks = []
        elif blkt=='table':
            pass
        else:
            print(f"Unknown type {blkt}")
        tmpblks.append(blk)
    return dayquotes
# read in a document 
my_doc = docx.Document( sys.argv[1])
# coerce to JSON using the standard options
mjson = simplify(my_doc)

dayquotes = parse_monthdoc(mjson)
print(len(dayquotes))
# or with non-standard options
#my_doc_as_json = simplify(my_doc,{"remove-leading-white-space":False})
