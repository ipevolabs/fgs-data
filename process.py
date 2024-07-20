import docx
import sys
from simplify_docx import simplify

def parse_paragraph( parav):
    assert len(parav)==1, "length of 'paragraph' is not 1"
    parav0 = parav[0]['VALUE']
    print(parav0)

def parse_table( tablev):
    assert len(tablev)==1, "length of 'table' is not 1"
    tablev0=tablev[0] 
    print(tablev0)


def tryparse( dd):
    assert dd['TYPE']=='document', "not begin with a 'document'"
    dv = dd['VALUE']
    assert len(dv)==1, "length of 'document' is not 1"
    dv0 = dv[0]
    assert dv0['TYPE']=='body', "the first element of 'document' is not a 'body'"
    bodyv = dv0['VALUE']
    print(f'{len(bodyv)} blocks')
    #para0 = bodyv[0]
    for idx, blk in enumerate(bodyv):
        #assert para['TYPE']=='paragraph'
        blkt = blk['TYPE']
        blkv = blk['VALUE']
        print(f'block {idx} type {blkt}')
        if blkt=='paragraph':
            parse_paragraph( blkv)
        elif blkt=='table':
            parse_table(blkv)
        else:
            print(f"Unknown type {blkt}")

    #    print(
# read in a document 
my_doc = docx.Document( sys.argv[1])
# coerce to JSON using the standard options
mjson = simplify(my_doc)

tryparse(mjson)
# or with non-standard options
#my_doc_as_json = simplify(my_doc,{"remove-leading-white-space":False})
