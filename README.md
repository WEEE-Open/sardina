# 🐟 S.A.R.D.I.N.A. 🐟
Statistiche Amabili Rendimento Degli Informatici Nell’Anno

## What

A Python script to quickly compute how much we've worked in terms of:
- Yearly commits
- Contributors commits
- Lines of code (LOC)
- Language usage statistics

all four both per repository and total. And it also generates cool graphs!

![combined stats graphs](docs/combined.svg)

All non-archived and non-disabled public repos are taken into consideration.

## Where

You can try out this repository directly in the browser at [this link](https://softweeere.caste.dev)!

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

First of all, generate a Personal Access Token (PAT) from your GitHub's [developer settings](https://github.com/settings/tokens) page.  
The token only needs access to the APIs so you can leave all the permission boxes unticked and generate a token that can only access your public information and has no control over your account, but still benefit from the 5000 API requests per hour of authenticated requests.  

You can skip this step if you want and use the script without a PAT, but you will be subject to a limit of 60 API requests per hour, which means you could only fetch complete statistics for an account with at most 30 repos (we have 32 at the moment, so a PAT is highly recommended).

The configuration is done in `config.py`. There you can paste your PAT generated at the previous step, and configure for which owner you want to see the stats (either a user or an organization), where you want to save the output, and if you want to run the script in development mode.

``` shell script
git clone https://github.com/weee-open/sardina
cd sardina

# Optional: if you want to use a virtual environment
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
vim config.py
./main.py

# If you opted to use a virtual environment
deactivate
```

### Command line options
```shell script
./main.py --help                               
usage: main.py [-h] [--cloc | --wc] [--commits | --no-commits] [--sloc | --no-sloc] [--graphs | --no-graphs] [--lang | --no-lang] [-p]

S.A.R.D.I.N.A. - Statistiche Amabili Rendimento Degli Informatici Nell'Anno

optional arguments:
-h, --help    show this help message and exit
-p, --ping    Re-trigger stats generation on GitHub servers. Useful with cron.

Software to use to count lines of code:
--cloc        Use CLOC to count SLOC.
--wc          Use WC to count SLOC.

Count contributions to all repositories:
--commits     Count commits.
--no-commits  Do not count commits.

Count SLOC (source lines of code) of repositories:
--sloc        Count SLOC.
--no-sloc     Do not count SLOC.

Generate graphs for the gathered statistics:
--graphs      Generate graphs.
--no-graphs   Do not generate graphs.

Generate language usage statistics:
--lang        Generate langauge statistics.
--no-lang     Do not generate language statistics.
```

## Language usage statistics

If SLOC are being counted and `cloc` is being used for that task, language statistics are always generated using CLOC itself independently of the `--lang` or `--no-lang` command line option (in this scenario no prompt is presented in interactive mode either). If SLOC are not being counted or `wc` is being used for that task, then language statistics are generated using GitHub's APIs only if the `--lang` option is specified. This happens because cloc is much more precise in counting the language usage than GitHub's APIs, and also is free in terms of API requests and Internet usage.

## Development

Having to make all the necessary requests and clone all the repositories in order to test changes to the program is long, makes having a stable internet connection a requirement and hammers GitHub's servers with unnecessary requests. Therefore we included a couple of options into `config.py` that can make a developer's job simpler:

* `dev_mode`: enables local caching of all GitHub API responses (list of repos, contributions and other statistics)
* `keep_repos`: enables long-term storage of cloned repositories instead of deleting them after each run. Keep in mind your available storage!
