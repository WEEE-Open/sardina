# 🐟 S.A.R.D.I.N.A. 🐟
Statistiche Amabili Rendimento Degli Informatici Nell’Anno

## What

A Python script to quickly compute how much we've worked in terms of:
- yearly commits
- contributors commits
- LOC  

all three both per repository and total.

All non-archived and non-disabled public repos are taken into consideration.

## How

Count our commits:
- some 🐍 magic
- GitHub [APIs](https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics)
- the `requests` library

Count our SLOC (Source Lines Of Code): 
- `git ls-files` to list repo files
- `sed '/^\s*$/d' $file` to remove whitespace-only lines
- `wc -l` to count lines  
or, optionally
- `cloc` - a dedicated [utility](https://github.com/AlDanial/cloc) to count lines of code

## Why

For our yearly report and recruitment presentation.  
Also, we are curious nerds.

## I want to run it now!

`git clone https://github.com/weee-open/sardina`  
`cd sardina`  
optional: `python3 -m venv venv`  
optional: `source venv/bin/activate`  
`pip install requests`  
`python main.py`