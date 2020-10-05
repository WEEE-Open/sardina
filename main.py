import requests
from time import sleep
from subprocess import run

url_clone = "https://github.com"
url_api = "https://api.github.com"
owner = "weee-open"
ignored_files = ["*.txt", "*.md", "LICENSE", ".gitignore"]


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


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

    stats = {}
    for repo in repos:
        while True:
            response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")
            if response.status_code == 403:
                raise_rate_limited_exception()
            elif response.status_code == 200:
                stats[repo] = sum([weekly['total'] for weekly in response.json()])
                break
            # else status == 202, stats are being computed by GitHub
            # sleep a lot to prevent spamming requests and getting rate-limited
            sleep(120)

    return stats


def _cleanup_repos(repos):
    for repo in repos:
        run(f"rm -rf {repo}".split())


def get_lines_stats(repos):
    stats = {'total': 0}
    ignored = " ".join([f"':!:{file}'" for file in ignored_files])
    _cleanup_repos(repos)

    for i, repo in enumerate(repos):
        run(f"git clone {url_clone}/{owner}/{repo}".split())

        git_files = run(f"cd {repo} && git ls-files -- . {ignored} && cd ..",
                        shell=True, text=True, capture_output=True).stdout.splitlines()
        # remove blank / whitespace-only lines
        for file in git_files:
            run(f"sed '/^\s*$/d' {repo}/{file} &> /dev/null", shell=True)

        stats[repo] = int(run(f"cd {repo} && wc -l $(git ls-files -- . {ignored}) && cd ..",
                              shell=True,
                              text=True,
                              capture_output=True).stdout.splitlines()[-1].split(" ")[-2])

        print(f"{i + 1}/{len(repos)} -- {stats[repo]} total non-blank lines in repo {repo}")
        stats['total'] += stats[repo]
        run(f"rm -rf {repo}".split())

    return stats


def print_all_stats(commits_stats, lines_stats):
    commits_output = "\n".join([f"{repo}: {commits_stats[repo]} commits past year"
                                for repo in commits_stats])
    commits_output += f"\nTotal commits of past year: {commits_stats['total']}"

    lines_output = "\n".join([f"{repo}: {lines_stats[repo]} lines total"
                              for repo in lines_stats])
    lines_output += f"Total LOC: {lines_stats['total']}"

    print(f"{commits_output}\n{'*' * 42}\n{lines_output}")


def main():
    repos = get_repos()
    commits_stats = get_commits_stats(repos, first_time_in_a_long_time=False)
    lines_stats = get_lines_stats(repos)
    print_all_stats(commits_stats, lines_stats)


if __name__ == "__main__":
    main()
