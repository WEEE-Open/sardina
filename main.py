import requests
from time import sleep

url_clone = "https://github.com"
url_api = "https://api.github.com"
owner = "weee-open"


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


def get_repos():
    try:
        return [repo['name'] for repo in requests.get(f"{url_api}/users/{owner}/repos").json()]
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
    pass


def print_all_stats(commits_stats, lines_stats):
    pass


def main():
    repos = get_repos()
    # commits_stats = get_commits_stats(repos)
    lines_stats = get_lines_stats(repos)
    print_all_stats(None, lines_stats)


if __name__ == "__main__":
    main()
