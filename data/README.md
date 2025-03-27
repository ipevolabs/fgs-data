## convert tsv for excel
```
tr '\t' ',' < fgsft_202503.tsv  > fgsft_xx.csv
printf '\xEF\xBB\xBF' | cat -  fgsft_xx.csv > fgsft_202503.csv
```
