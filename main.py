import requests
from datetime import datetime, timedelta
from subprocess import run

from ignored_files import ignored_files

url_clone = "https://github.com"
url_api = "https://api.github.com"
owner = "weee-open"
output_file = "stats"


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


def raise_cloc_not_installed_exception():
    raise Exception("cloc is not installed.\n"
                    "Install it from https://github.com/AlDanial/cloc or use wc to count lines") from None


def get_repos() -> list:
    try:
        return [repo['name']
                for repo in requests.get(f"{url_api}/users/{owner}/repos").json()
                if not repo['archived'] and not repo['disabled']]
    except TypeError:
        raise_rate_limited_exception()


def get_anonymous_commits_stats(repos: list) -> dict:
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics
    stats = {'total': 0}
    already_checked_repos = []
    trigger_stats = False

    for repo in repos:
        response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")
        print(f"{repo} gave response {response.status_code}")

        if response.status_code == 403:
            raise_rate_limited_exception()
        elif response.status_code == 200:
            stats[repo] = sum([weekly['total'] for weekly in response.json()])
            stats['total'] += stats[repo]
            already_checked_repos.append(repo)
        else:  # status_code == 202, stats are being computed by GitHub
            trigger_stats = True

    if trigger_stats:
        print("Triggering stats generation on GitHub's servers for remaining repos, "
              "re-run this script in >10 minutes to get their stats as well...")
        for repo in [r for r in repos if r not in already_checked_repos]:
            requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")

    print("\n")
    return stats


def get_contributors_commits_stats(repos: list) -> dict:
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#get-all-contributor-commit-activity
    stats = {'total': {}, 'past_year': {}}
    unix_one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp())

    for repo in repos:
        response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/contributors")
        print(f"{repo} gave response {response.status_code}")

        if response.status_code == 403:
            raise_rate_limited_exception()

        elif response.status_code == 200:
            json = response.json()
            stats[repo] = {
                'total': {author['author']['login']: author['total']
                          for author in json},
                'past_year': {author['author']['login']: sum(week['c']
                                                             for week in author['weeks']
                                                             if week['w'] > unix_one_year_ago)
                              for author in json},
            }

            for author in json:
                login = author['author']['login']
                if login not in stats['total']:
                    stats['total'][login] = 0
                    stats['past_year'][login] = 0
                stats['total'][login] += author['total']
                stats['past_year'][login] += sum(week['c']
                                                 for week in author['weeks']
                                                 if week['w'] > unix_one_year_ago)

    print("\n")
    return stats


def _cleanup_repos(repos: list):
    for repo in repos:
        run(f"rm -rf {repo}".split())


def get_lines_stats(repos: list, use_cloc: bool) -> dict:
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


def print_all_stats(commits_stats: dict, lines_stats: dict, use_cloc: bool):
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

    output = f"{commits_output}\n\n{'*' * 42}\n\n{lines_output}"
    print(f"\n\n{output}")
    with open(f"{output_file} {datetime.now()}.txt", 'w') as out:
        out.write(f"Stats generated via https://github.com/weee-open/sardina\n"
                  f"use_cloc={use_cloc}\n"
                  f"\n{output}")


def main():
    use_cloc = input("Do you want to use cloc (C) or wc (W) to count SLOC? c/W ").lower() == "c"
    get_commits = input("Do you want to get the commits stats? It may take a long time due to GitHub servers updating "
                        "their cache. y/N ").lower() == "y"

    repos = get_repos()
    commits_stats = get_anonymous_commits_stats(repos) if get_commits else None
    contributors_stats = get_contributors_commits_stats(repos) if get_commits else None
    lines_stats = get_lines_stats(repos, use_cloc)
    print_all_stats(commits_stats, lines_stats, use_cloc)


if __name__ == "__main__":
    main()
