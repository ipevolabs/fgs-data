## Installation
* get the source code
```
git clone https://github.com/ipevolabs/fgs-data.git
```
* setup python virtual environment
```
python -m venv .venv
. .venv/bin/activate
```
* install dependencies
```
pip install -r requirements.txt
```

## example usage
* change directory
```
cd wer
```
* if no argument, it shows the command line format
```
$ python calcwer.py 
Usage: calcwer.py <reference text file> <hypothesis text file> [number of lines to calculate]
```
* test the built-in samples
```
$ python calcwer.py sb_reference.txt sb_hypothesis.txt
Building prefix dict from the default dictionary ...
Loading model from cache /tmp/jieba.cache
Loading model cost 1.255 seconds.
Prefix dict has been built successfully.
sentence 1
REF: 大家 吉祥 今天 要 跟 大家 談 人生 行路 這 
....
number of sentences: 1
substitutions=58 deletions=14 insertions=55 hits=1440

mer=8.10%
wil=11.69%
wip=88.31%
wer=8.40%
```

`wer=8.40%` is the WER.

* just test first 5 sentecences
```
$ python calcwer.py sb_reference.txt sb_hypothesis.txt 5

Building prefix dict from the default dictionary ...
Loading model from cache /tmp/jieba.cache
Loading model cost 1.240 seconds.
Prefix dict has been built successfully.
sentence 1
REF: 大家 吉祥 今天 要 跟 大家 談 人生 行路 這 是 出自 * 老舍 的 一 個 文章 老舍 本身 是 一位 文 學 家 他 一生 可以 說 留下 很多
HYP: 大家 吉祥 今天 要 跟 大家 談 人生 行路 這 是 出自 老  神 的 一 個 文章 老舍 本身 是 一位 文 學 家 * ** ** * ** **
                                    I  S                           D  D  D D  D  D

number of sentences: 1
substitutions=1 deletions=6 insertions=1 hits=23

mer=25.81%
wil=29.47%
wip=70.53%
wer=26.67%
```

## FAQ
### Why does it always show `number of sentences: 1`? this text files have so many sentences.
* We combine all sentences into one to avoid the problem difference sentence segmentation between reference and hypothesis text.
### 為什麼狀聲字詞都認定譯錯？ 明明語音裡有發這些音啊
通常是主講者的確有發, 原文稿為了優雅, 刻意拿掉, 遇到此情況請修改原稿. 
 