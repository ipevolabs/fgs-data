from typing import List, Dict
import jiwer
from jiwer import transforms
import jieba  # Chinese word segmentation library


def read_files( refpath:str, hypopath:str) -> List[str]:
    nfstrs = []
    for fpath in [refpath, hypopath]:
        with open(fpath, "r", encoding="utf-8") as f:
            fstr = f.read()
        nfstrs.append(fstr)
    return nfstrs


def read_links():
    import requests

    hypolink = "https://gist.github.com/timwu-ipevo/6a7fb0b6547e0d83b05a13e7d703e8ba/raw/f92a8efc257ba339af50bd68a1efad7449120a51/sb_hypothesis.txt"
    reflink = "https://gist.github.com/timwu-ipevo/6a7fb0b6547e0d83b05a13e7d703e8ba/raw/f92a8efc257ba339af50bd68a1efad7449120a51/sb_reference.txt"

    refstr = requests.get(reflink).text
    hypostr = requests.get(hypolink).text
    return [refstr, hypostr]


def to_multi_lines(texts):
    return [text for text in texts.split("\n") if text.strip() != ""]


# rewrite ChineseTransform as a function
def chinese_transform(texts: List[str]) -> List[str]:
    chinese_punc = "，。！？；：" "''（）【】《》、…"
    newtexts = []
    for text in texts:
        text = text.strip()
        # Remove Chinese and English punctuation
        for punct in chinese_punc:
            text = text.replace(punct, "")
        # Segment Chinese text into words using jieba
        words = jieba.cut(text, cut_all=False, HMM=False)
        # Join with spaces to make it compatible with jiwer
        newtext = " ".join(words)
        newtexts.append(newtext)
    return newtexts


def calculate_chinese_wer2(ground_truth: str, hypothesis: str, hslice):
    if True:
        ground_truth_mlines = to_multi_lines(ground_truth)
        hypothesis_mlines = to_multi_lines(hypothesis)
        ground_truth_mlines = chinese_transform(ground_truth_mlines[hslice])
        hypothesis_mlines = chinese_transform(hypothesis_mlines[hslice])
        ground_truth = " ".join(ground_truth_mlines)
        hypothesis = " ".join(hypothesis_mlines)

    out = jiwer.process_words(
        ground_truth, hypothesis
    )
    print(jiwer.visualize_alignment(out))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: {} <reference text file> <hypothesis text file> [number of lines to calculate]".format(sys.argv[0]))
        sys.exit(1)
    
    refpath = sys.argv[1]
    hypopath = sys.argv[2]
    numlines = 1000
    if len(sys.argv) > 3:
        numlines = int(sys.argv[3])
    
    [refstr, hypostr] = read_files(refpath, hypopath)
    calculate_chinese_wer2(refstr, hypostr, slice(0, numlines))
