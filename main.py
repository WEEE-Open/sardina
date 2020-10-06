import requests
from time import sleep
from subprocess import run

from ignored_files import ignored_files

url_clone = "https://github.com"
url_api = "https://api.github.com"
owner = "weee-open"


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


def raise_cloc_not_installed_exception():
    raise Exception("cloc is not installed.\n"
                    "Install it from https://github.com/AlDanial/cloc or use wc to count lines") from None


def get_repos():
    try:
        return [repo['name']
                for repo in requests.get(f"{url_api}/users/{owner}/repos").json()
                if not repo['archived'] and not repo['disabled']]
    except TypeError:
        raise_rate_limited_exception()


def get_commits_stats(repos, first_time_in_a_long_time=False):
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics
    # trigger GitHub's stats computing for each repo without looking at response code
    if first_time_in_a_long_time:
        for repo in repos:
            requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")

    stats = {'total': 0}
    for repo in repos:
        while True:
            response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")
            if response.status_code == 403:
                raise_rate_limited_exception()
            elif response.status_code == 200:
                stats[repo] = sum([weekly['total'] for weekly in response.json()])
                stats['total'] += stats[repo]
                break
            # else status == 202, stats are being computed by GitHub
            # sleep a lot to prevent spamming requests and getting rate-limited
            print(f"{repo} gave response {response.status_code}, sleeping 2 minutes before retrying...")
            sleep(120)

    return stats


def _cleanup_repos(repos):
    for repo in repos:
        run(f"rm -rf {repo}".split())


def get_lines_stats(repos, use_cloc):
    stats = {'total': {'sloc': 0, 'all': 0}} if use_cloc else {'total': 0}
    ignored = " ".join([f"':!:{file}'" for file in ignored_files])
    _cleanup_repos(repos)

    for i, repo in enumerate(repos):
        run(f"git clone {url_clone}/{owner}/{repo}".split())

        if use_cloc:
            try:
                cloc_out = run(f"cloc --csv {repo}",
                               shell=True,
                               text=True,
                               capture_output=True).stdout.splitlines()[-1]

                stats[repo] = {
                    'sloc': int(cloc_out.split(",")[-1]) or 0,
                    'comments': int(cloc_out.split(",")[-2]) or 0,
                    'blanks': int(cloc_out.split(",")[-3]) or 0,
                }

                stats['total']['sloc'] += stats[repo]['sloc']
                stats['total']['all'] += stats[repo]['sloc'] + stats[repo]['comments'] + stats[repo]['blanks']

            except IndexError:
                raise_cloc_not_installed_exception()

        else:
            git_files = run(f"cd {repo} && git ls-files -- . {ignored} && cd ..",
                            shell=True, text=True, capture_output=True).stdout.splitlines()
            # remove blank / whitespace-only lines
            for file in git_files:
                run(f"sed '/^\s*$/d' {repo}/{file} &> /dev/null", shell=True)

            stats[repo] = int(run(f"cd {repo} && wc -l $(git ls-files -- . {ignored}) && cd ..",
                                  shell=True,
                                  text=True,
                                  capture_output=True).stdout.splitlines()[-1].split(" ")[-2])

            stats['total'] += stats[repo]

        print(f"{i + 1}/{len(repos)} -- {stats[repo]['sloc'] if use_cloc else stats[repo]} "
              f"total non-blank lines in repo {repo}")
        run(f"rm -rf {repo}".split())

    return stats


def print_all_stats(commits_stats, lines_stats, use_cloc):
    if commits_stats is not None:
        commits_output = "\n".join([f"{repo}: {commits_stats[repo]} commits past year"
                                    for repo in commits_stats
                                    if repo != "total"])
        commits_output += f"\nTotal commits of past year: {commits_stats['total']}"
    else:
        commits_output = "No commits stats, as you've selected at the beginning."

    if use_cloc:
        lines_output = "\n".join([f"{repo}: {lines_stats[repo]['sloc']} sloc - "
                                  f"{lines_stats[repo]['comments']} comments - "
                                  f"{lines_stats[repo]['blanks']} blank lines - "
                                  f"{lines_stats[repo]['sloc'] + lines_stats[repo]['comments'] + lines_stats[repo]['blanks']} total"
                                  for repo in lines_stats
                                  if repo != "total"])
        lines_output += f"\nTotal SLOC: {lines_stats['total']['sloc']}" \
                        f"\nTotal lines including comments and blanks: {lines_stats['total']['all']}"

    else:
        lines_output = "\n".join([f"{repo}: {lines_stats[repo]} lines total"
                                  for repo in lines_stats
                                  if repo != "total"])
        lines_output += f"\nTotal SLOC: {lines_stats['total']}"

    print(f"\n\n{commits_output}\n\n{'*' * 42}\n\n{lines_output}")


def main():
    use_cloc = input("Do you want to use cloc (C) or wc (W) to count SLOC? c/W ").lower() == "c"
    get_commits = input("Do you want to get the commits stats? It may take a long time due to GitHub servers updating "
                        "their cache. y/N ").lower() == "y"

    repos = get_repos()
    commits_stats = get_commits_stats(repos, first_time_in_a_long_time=True) if get_commits else None
    lines_stats = get_lines_stats(repos, use_cloc)
    print_all_stats(commits_stats, lines_stats, use_cloc)


if __name__ == "__main__":
    main()
