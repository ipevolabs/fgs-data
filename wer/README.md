## Installation

1. Clone the repository:
	```sh
	git clone https://github.com/ipevolabs/fgs-data.git
	```

2. Set up a Python virtual environment:
	```sh
	python -m venv .venv
	source .venv/bin/activate
	```

3. Install dependencies:
	```sh
	pip install -r requirements.txt
	```

## Example Usage

1. Change directory:
	```sh
	cd wer
	```

2. Display command line format (if no arguments are provided):
	```sh
	python calcwer.py
	```
	Output:
	```
	Usage: calcwer.py <reference text file> <hypothesis text file> [number of lines to calculate]
	```

3. Test with built-in samples:
	```sh
	python calcwer.py sb_reference.txt sb_hypothesis.txt
	```
	Output:
	```
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

	`wer=8.40%` is the Word Error Rate (WER).

4. Test the first 5 sentences:
	```sh
	python calcwer.py sb_reference.txt sb_hypothesis.txt 5
	```
	Output:
	```
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

### Why does it always show `number of sentences: 1`? The text files have many sentences.

We combine all sentences into one to avoid issues with different sentence segmentation between the reference and hypothesis texts.

### 為什麼狀聲字詞都認定譯錯？ 明明語音裡有發這些音啊

通常是主講者的確有發, 原文稿為了優雅, 刻意拿掉, 遇到此情況請修改原稿.