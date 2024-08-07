## Setup
```
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

## Example Usage

```
python process.py 01.docx
```

## List of Narrative Playlists
could be used as testing datasets
* Jan: https://youtube.com/playlist?list=PLRcizuixTNe-Qz77MlFMH9kpVZ12y3Mf6&si=8om6BKYXFX_8Fktb
* Feb: https://youtube.com/playlist?list=PLRcizuixTNe_YlfqnFjq0S6NS3HDKleBf&si=r37CLp_i0e34EaB0
* March: https://youtube.com/playlist?list=PLRcizuixTNe_DUA06ahlccyz3Q0gKPLTv&si=_xODaT45mCcnzjYK
* April: https://youtube.com/playlist?list=PLRcizuixTNe-aCGw8bl3ucFDulQCNbfwy&si=WqErfJ_iFsnETvAj
* May: https://youtube.com/playlist?list=PLRcizuixTNe9A42S5m8lZKBD_g2kBhhuA&si=1hvVP-dW-_xRoyhG
* June: https://youtube.com/playlist?list=PLRcizuixTNe-drD11UL-osZoZtQF0VqGP&si=dcpL5N05EM9eUd7j
* Aug: https://youtube.com/playlist?list=PLRcizuixTNe-mNxmRw1TRdHkvGNA3q7D4&si=OCf9hDtuIUdH6Tjq
* Dec: https://youtube.com/playlist?list=PLRcizuixTNe8E-ExcCerY4WHhQ18VCY4G&si=U_cphBMdTo21uca4

### Glossary
* convert it to UTF-8 first
```sh
iconv -t utf8 -f big5 hb_glossary.txt > hb_glossary_v2_utf8.txt
```

* example usage:
generating 4 sentences per entry from entry 100 to 200 in `hb_glossary_vt_utf8.txt` using model `gpt-4o`
```
python hb_process.py hb_glossary_v2_utf8.txt --skip=100 --endidx=200 --nsentences=4 --model="gpt-4o" --outfile=fgsft1.jsonl
```
if everything goes well, the augumented data should be in `fgsft1.jsonl`

### Post augumentation fix
It happens time to time that some of these augumented entries are malform.  We proposed a tool to fix it.
* example usage
```
python  filter_dataset.py fgsft2.jsonl
```

* example output
```
fix entries:
{'normal': 4365, 'malform': 0, 'multi': 19, 'multi2': 9, 'no_en': 1, 'extra_list': 4, 'inconsist_en': 6, 'others': 0}
number of fixed entries: 112
fixed_fgs.jsonl saved
```

### Convert for finetune
```
python fgsda_to_oaift.py fgsft3.jsonl fgsoai
```
```
Map: 100%|████████████████████████████████████████████████████████████| 4474/4474 [00:00<00:00, 64330.87 examples/s]
Map: 100%|██████████████████████████████████████████████████████████| 22566/22566 [00:00<00:00, 67042.69 examples/s]
Creating json from Arrow format: 100%|█████████████████████████████████████████████| 23/23 [00:00<00:00, 327.80ba/s]
Finetune dataset file fgsoai.jsonl saved. File is valid = True
```

You can upload `fgsoai.jsonl` to OpenAI finetune console to create a new finetune job.
