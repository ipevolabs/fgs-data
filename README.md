# fgs-data

Fo Guang Shan (佛光山) Buddhist glossary data, and the tooling that turns it into
Chinese→English translation datasets.

Buddhist material is hard to translate consistently. 般若 is rendered "Prajna" in
one glossary entry and "Wisdom" in the next; 國際佛光會 has an official English
name (Buddha's Light International Association) that no general-purpose model
reliably produces. This repository collects the bilingual source material that
Fo Guang Shan and the BLIA have already settled on, and builds from it the
datasets needed to make a translator — finetuned or retrieval-augmented — use
that same vocabulary every time.

## What's here

**Source material**

* `blia_terminology.tsv`, `hb_glossary_v2v3.tsv` — zh↔en terminology glossaries
  (~200 and ~9,700 entries), from BLIA organisational names to sutra titles and
  full couplets.
* `01.docx` … `12.docx` — a year of side-by-side bilingual daily readings
  (Venerable Master Hsing Yun's 祈願文 and Pearls of Wisdom pieces, one file per
  month), stored as zh/en table pairs.
* `data/*.jsonl` — the augmented and finetune-ready datasets derived from the
  above.

**Pipeline**

| Stage | Tool |
|---|---|
| Extract zh/en pairs from the `.docx` readings | `process.py` |
| Merge, de-duplicate and correct glossary files | `hb_utils.py` |
| Expand bare glossary phrases into full example sentence pairs via an LLM | `hb_process.py`, `glossary_augumentation.py` |
| Repair malformed augmented entries | `filter_dataset.py` |
| Convert to OpenAI chat format and run the finetune | `fgsda_to_oaift.py`, `openai_finetune.py` |
| Chat with the resulting model | `testftm_ui.py` (Chainlit) |

**Retrieval instead of finetuning**

Two proofs-of-concept replace the finetuned translator with retrieval at
inference time, so new terminology lands without retraining:

* `azure_rag_poc.py` — hybrid keyword + vector retrieval over Azure AI Search.
* `grep_rag_poc.py` — no embeddings and no vector store at all; an LLM drives
  plain `grep` over the translation memory in a loop. Written up in
  `grep-based-rag.md`.

**Evaluation**

* `wer/` — Word Error Rate for ASR transcripts of these talks, with jieba
  segmentation for Chinese. See `wer/README.md`.
* `ytplaylists.py` — pulls the YouTube playlists listed below, used as test audio.

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

### UI test
```
chainlit run --port 8100 testftm_ui.py -w
```

### Find duplicated entries
```
python hb_utils.py listdup blia_terminology.tsv hb_glossary_v2v3.tsv > blipdup.txt 
```

### Adjust entries
It can merge and adjust multiple glossory files in TSV format
```
python hb_utils.py adjust blia_terminology.tsv blia_terminology_0327.tsv > blia_terminology_corrected.tsv 
python hb_utils.py adjust blia_terminology_0327.tsv > blia_terminology_corrected.tsv 
```

### Dump the augumented entries(for finetune) in a readable form
python hb_utils.py dumpftjson fgsft_202503.jsonl > fgsft_202503.csv

## License

The code in this repository is released under the [MIT License](LICENSE.txt).

Note that the glossaries, transcripts (`*.docx`) and derived datasets bundled
here originate from third-party Fo Guang Shan / BLIA material. The MIT license
covers this repository's own code and does not grant rights to that underlying
source material — check with the rights holder before redistributing it.
