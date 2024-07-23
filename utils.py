import re
def parse_date(date_str):
    # Define a regex pattern to capture the date parts  
    #pattern = r"(\d{1,2})月(\d{1,2})日([A-Za-z]+ \d{1,2}(st|nd|rd|th)?)" 
    pattern = r"(\d{1,2})月(\d{1,2})日(?:[A-Za-z]+ \d{1,2}(st|nd|rd|th)?)?"  
    # Search for the pattern in the string  
    match = re.search(pattern, date_str) 
    if not match:
        return 0, 0
    # Extract the parts from the match  
    month_zh, day_zh, date_en = match.groups()[:3]  
    # Convert the Chinese month and day to integers  
    month = int(month_zh)  
    day = int(day_zh)  
    return month, day  

"""
"zh": "功不唐捐\n◎胡適（1891～1962）\n生命本沒有意義，你要能給它什麼意義，他就有什麼意義。\r與其終日冥想人生有何意義，不如試用此生做點有意義的事。\n大膽的假設，小心的求證；認真的做事，嚴肅的做人。\n我們要深信：今日的失敗，都由於過去的不努力。 \r我們要深信：今日的努力，必定有將來的大收成。\n朋友們，在你最悲觀最失望的時候，那正是你必須鼓起堅強的信心的時候。你要深信：天下沒有白費的努力。成功不必在我，而功力必不唐捐。\n昨日種種，皆成今我，切莫思量，更莫哀。\r從今往後，怎麼收穫，就怎麼栽。\n──選自《胡適全集》",
"en": "No Effort Goes in Vain\nHu Shih (1891 - 1962)\nEnglish translation: Miao Guang and Rosalyna Huang\nLife on its own does not mean anything──it takes on any meaning that you decide to give it. Instead of spending all day contemplating the meaning of life, we may as well attempt to do something that gives it one.\nBe bold when making a case and cautious in seeking evidence; be earnest with all matters, and solemn in your conduct.\nWe must be firm, believing that today's failure is yesterday's lack of hard work. We must be firm, believing that today's hard work will surely lead to tomorrow's great success.\nO friends! The moments when you feel the saddest and most disappointed are the times when you need a courageous and strong faith the most. Firmly believe that no hard work ever goes wasted in this world. I do not need to be the one to succeed, but no effort will be in vain.\nEvery part of yesterday makes up what I am today; Don't think too far ahead or grieve. From now on, I shall reap as I sow.\n── from Hushi Quanji\n(Complete Works of Hu Shih)"
"""

def extract_author_zh( s):
    if s=='':
        return ''
    s = s.strip(' ◎')
    # Substituting the pattern with an empty string  
    return re.sub(r'（.*?）', '', s)

def find_cite_line( lines):
    for i in range(len(lines) - 1, -1, -1):  
        if  '──選自' in lines[i]:
            return i
    return -1

def extract_quote_meta_zh(lines):
    if '◎' in lines[0]:
        [titleline, authorline] = lines[0].split('◎')
    else:
        [titleline, authorline] = [lines[0], lines[1]]
        if not '◎' in authorline:
            authorline=''
    ## extract title
    title = titleline.strip(' 　') #space char in half and full
 
    ## extract author
    author = extract_author_zh(authorline)

    ## extract cite_from
    cite_from=''
    ci = find_cite_line(lines)
    if ci>=0:    
        line = lines[ci]
        match = re.search(r'《(.*?)》', line)
        if match:
            cite_from = match.group(1)
        else:
            cite_from = line
    return ( title, author, cite_from)

def extract_quote_meta_en(text):
    return None

if __name__ == "__main__":  
    # Example usage  
    date_str = "1月28日January 28th" 
    date_str = "1月6日January 6th"
    month, day = parse_date(date_str)  
    print(f"Month: {month}, Day: {day}")  # Output: Month: 1, Day: 28

