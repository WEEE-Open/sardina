import requests
from time import sleep

url = "https://api.github.com"
owner = "weee-open"


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


try:
    repos = [repo['name'] for repo in requests.get(f"{url}/users/{owner}/repos").json()]
except TypeError:
    raise_rate_limited_exception()

# see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics
# trigger GitHub's stats computing for each repo without looking at response code
for repo in repos:
    requests.get(f"{url}/repos/{owner}/{repo}/stats/commit_activity")

stats = {}
for repo in repos:
    while True:
        response = requests.get(f"{url}/repos/{owner}/{repo}/stats/commit_activity")
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
