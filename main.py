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


def get_commits_stats(repos):
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics
    # trigger GitHub's stats computing for each repo without looking at response code
    for repo in repos:
        requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")

    stats = {}
    for repo in repos:
        while True:
            response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity")
            if response.status_code == 403:
                raise_rate_limited_exception()
            elif response.status_code == 200:
                stats[repo] = response.json()
                break
            # else status == 202, stats are being computed by GitHub
            # sleep a lot to prevent spamming requests and getting rate-limited
            sleep(120)

    for repo in stats:
        pass


def get_lines_stats(repos):
    stats = {'total': 0}
    ignored = " ".join([f"':!:{file}'" for file in ignored_files])
    for repo in repos:
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
        print(f"{stats[repo]} total non-blank lines in repo {repo}")
        stats['total'] += stats[repo]
        run(f"rm -rf {repo}".split())
    return stats


def print_all_stats(commits_stats, lines_stats):
    print(commits_stats)
    print(lines_stats)


def main():
    repos = get_repos()
    # TODO: implement get_commits_stats
    # commits_stats = get_commits_stats(repos)
    lines_stats = get_lines_stats(repos)
    print_all_stats(None, lines_stats)


if __name__ == "__main__":
    main()
