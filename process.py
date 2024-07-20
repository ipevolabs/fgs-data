import docx
import sys
from simplify_docx import simplify


def parse_paragraph( parav):
    if len(parav)==1:
        parav0 = parav[0]['VALUE']
        print(parav0)

def parse_table( tablev):
    print( len(tablev))


def tryparse( dd):
    assert dd['TYPE']=='document', "not begin with a 'document'"
    dv = dd['VALUE']
    assert len(dv)==1, "length of 'document' is not 1"
    dv0 = dv[0]
    assert dv0['TYPE']=='body', "the first element of 'document' is not a 'body'"
    bodyv = dv0['VALUE']
    print(f'{len(bodyv)} paragraphs')
    #para0 = bodyv[0]
    for blk in bodyv:
        #assert para['TYPE']=='paragraph'
        if blk['TYPE']=='paragraph':
            parse_paragraph(blk['VALUE'])
        elif blk['TYPE']=='table':
            parse_table(blk['VALUE'])
        else:
            print(f"Unknown type {blk['TYPE']}")

    #    print(
# read in a document 
my_doc = docx.Document( sys.argv[1])
# coerce to JSON using the standard options
mjson = simplify(my_doc)

tryparse(mjson)
# or with non-standard options
#my_doc_as_json = simplify(my_doc,{"remove-leading-white-space":False})
