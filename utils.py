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

if __name__ == "__main__":  
    # Example usage  
    date_str = "1月28日January 28th" 
    date_str = "1月6日January 6th"
    month, day = parse_date(date_str)  
    print(f"Month: {month}, Day: {day}")  # Output: Month: 1, Day: 28


