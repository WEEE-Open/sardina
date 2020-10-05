# 🐟 S.A.R.D.I.N.A. 🐟
Statistiche Amabili Rendimento Degli Informatici Nell’Anno

## What

A Python script to quickly compute how much we've worked in terms of
- yearly commits (per repo + total)
- LOC (per repo + total)

All non-archived and non-disabled public repos are taken into consideration.

## How

- `git ls-files` to list repo files
- `sed '/^\s*$/d' $file` to remove whitespace-only lines
- `wc -l` to count lines
- some 🐍 magic to contact GitHub's [APIs](https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics) (aka the `requests` library)

or, optionally

- `cloc` - a dedicated [utility](https://github.com/AlDanial/cloc) to count lines of code

## Why

For our yearly report and recruitment presentation.  

## I want to run it now!

`git clone https://github.com/weee-open/sardina`  
`cd sardina`  
`python3 -m venv venv`  
`source venv/bin/activate`  
`pip install requests`  
`python main.py`