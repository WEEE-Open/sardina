import requests
import re
import os
import json
import matplotlib.pyplot as plot
from typing import List
from datetime import datetime, timedelta
from subprocess import run

from ignored_files import ignored_files
from config import owner, is_organization, output_file, output_dir, token, \
                   dev_mode, keep_repos

url_clone = "https://github.com"
url_api = "https://api.github.com"


class Graph:
    def __init__(self,
                 data: dict = {},
                 minimum: int = 0,
                 min_count: int = 0,
                 kind: str = 'pie',
                 legend: str = 'Default graph legend',
                 title: str = 'Default graph title'):

        self.minimum = minimum
        self.min_count = min_count
        self.kind = kind
        self.legend = legend
        self.title = title
        
        self.data = _normalize_data(data, minimum)
        self.count = len(self.data)

    def is_suitable(self) -> bool:
        return True if len(self.data) >= self.min_count else False


def raise_rate_limited_exception():
    raise Exception("You are getting rate-limited by GitHub's servers. Try again in a few minutes.") from None


def raise_cloc_not_installed_exception():
    raise Exception("cloc is not installed.\n"
                    "Install it from https://github.com/AlDanial/cloc or use wc to count lines") from None


def get_repos(header: dict) -> list:
    url = f'{url_api}/{"orgs" if is_organization else "users"}/{owner}/repos?per_page=100'
    pages = 1

    # As of the time of writing, we don't *need* pagination as we have < 100 repos, but just for future proofing
    # here is code that can handle n pages of repositories
    try:
        if not (dev_mode and os.path.isfile('repos.json')):
            response = requests.get(url, headers=header)

            # If in devmode, cache the response in case it does not yet exist
            if dev_mode:
                with open('repos.json', 'w') as f:
                    json.dump(response.json(), f)

            repos = [repo['name'] for repo in response.json() if not repo['archived'] and not repo['disabled']]

            # If the result page is only one page long, no link header is present
            if 'link' in response.headers:
                for link in response.headers['link'].split(','):
                    location, rel = link.split(';')

                    if rel.strip() == 'rel="last"':
                        pages = int(re.compile('&page=(?P<page>[0-9]+)').search(location).group('page'))

                for page in range(2, (pages + 1)):
                    response = requests.get(f'{url}&page={page}', headers=header)
                    repos += [repo['name'] for repo in response.json() if not repo['archived'] and not repo['disabled']]

        else:
            print('Using cache for repository information')
            with open('repos.json', 'r') as f:
                repos = [repo['name'] for repo in json.load(f) if not repo['archived'] and not repo['disabled']]

        # ignore case when sorting list of repos to prevent uppercase letters to come before lowercase letters
        return sorted(repos, key=str.casefold)

    except TypeError:
        raise_rate_limited_exception()


def get_anonymous_commits_stats(repos: list, header: dict) -> dict:
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#statistics
    stats = {'total': 0}

    if dev_mode:
        try:
            os.mkdir('repo-stats')
        except FileExistsError:
            pass

    print("\nGetting anonymous commits stats...")
    for i, repo in enumerate(repos):
        if(not (os.path.isfile(os.path.join('repo-stats', f'{repo}.anonymous.json')) and dev_mode)):
            response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/commit_activity", headers=header)

            # If in devmode, cache the response in case it does not yet exist
            if dev_mode:
                with open(os.path.join('repo-stats', f'{repo}.anonymous.json'), 'w') as f:
                    json.dump(response.json(), f)

            print(f"{i + 1}/{len(repos)} - {repo} - {'OK' if response.status_code == 200 else 'Awaiting new data...'}")

            if response.status_code == 403:
                raise_rate_limited_exception()
            elif response.status_code == 200:
                stats[repo] = sum([weekly['total'] for weekly in response.json()])
                stats['total'] += stats[repo]
        else:
            print(f'Using cache for repo {repo}')
            with open(os.path.join('repo-stats', f'{repo}.anonymous.json'), 'r') as f:
                stats[repo] = sum([weekly['total'] for weekly in json.load(f)])
                stats['total'] += stats[repo]

    print("\n")
    return stats


def get_contributors_commits_stats(repos: list, header: dict) -> dict:
    # see https://docs.github.com/en/free-pro-team@latest/rest/reference/repos#get-all-contributor-commit-activity
    stats = {'total': {}, 'past_year': {}}
    unix_one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp())

    if dev_mode:
        try:
            os.mkdir('repo-stats')
        except FileExistsError:
            pass

    print("Getting contributors commits stats...")
    for i, repo in enumerate(repos):
        if(not (os.path.isfile(os.path.join('repo-stats', f'{repo}.json')) and dev_mode)):
            response = requests.get(f"{url_api}/repos/{owner}/{repo}/stats/contributors", headers=header)

            # If in devmode, cache the response in case it does not yet exist
            if dev_mode:
                with open(os.path.join('repo-stats', f'{repo}.json'), 'w') as f:
                    json.dump(response.json(), f)

            print(f"{i + 1}/{len(repos)} - {repo} - {'OK' if response.status_code == 200 else 'Awaiting new data...'}")

            if response.status_code == 403:
                raise_rate_limited_exception()

            elif response.status_code == 200:
                json_response = response.json()

            else:
                print('\n')
                return stats

        else:
            print(f'Using cache for repo {repo}')
            with open(os.path.join('repo-stats', f'{repo}.json'), 'r') as f:
                json_response = json.load(f)

        stats[repo] = {
            'total': {author['author']['login']: author['total']
                      for author in json_response},
            'past_year': {author['author']['login']: sum(week['c']
                                                         for week in author['weeks']
                                                         if week['w'] > unix_one_year_ago)
                          for author in json_response},
        }

        for author in json_response:
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
    run("rm -rf repos".split())


def get_lines_stats(repos: list, use_cloc: bool) -> dict:
    stats = {'total': {'sloc': 0, 'all': 0}} if use_cloc else {'total': 0}
    ignored = " ".join([f"':!:{file}'" for file in ignored_files])

    if not (dev_mode and keep_repos):
        _cleanup_repos(repos)

    print("Getting SLOC stats...")

    try:
        os.mkdir('repos')
    except FileExistsError:
        pass

    for i, repo in enumerate(repos):
        if not os.path.isdir(os.path.join('repos', repo)):
            run(f"git clone {url_clone}/{owner}/{repo} {os.path.join('repos', repo)}".split())

        if use_cloc:
            try:
                cloc_out = run(f"cloc --csv {os.path.join('repos', repo)}",
                               shell=True,
                               text=True,
                               capture_output=True).stdout.splitlines()[-1]
                try:
                    stats[repo] = {
                        'sloc': int(cloc_out.split(",")[-1]) or 0,
                        'comments': int(cloc_out.split(",")[-2]) or 0,
                        'blanks': int(cloc_out.split(",")[-3]) or 0,
                    }
                except ValueError:  # there are no lines in this repository
                    stats[repo] = {
                        'sloc': 0,
                        'comments': 0,
                        'blanks': 0,
                    }

                stats['total']['sloc'] += stats[repo]['sloc']
                stats['total']['all'] += stats[repo]['sloc'] + stats[repo]['comments'] + stats[repo]['blanks']

            except IndexError:
                raise_cloc_not_installed_exception()

        else:
            git_files = run(f"cd {os.path.join('repos', repo)} && git ls-files -- . {ignored} && cd ..",
                            shell=True, text=True, capture_output=True).stdout.splitlines()
            # remove blank / whitespace-only lines
            for file in git_files:
                run(f"sed '/^\s*$/d' {os.path.join('repos', repo, file)} &> /dev/null", shell=True)

            stats[repo] = int(run(f"cd {os.path.join('repos', repo)} && wc -l $(git ls-files -- . {ignored}) && cd ..",
                                  shell=True,
                                  text=True,
                                  capture_output=True).stdout.splitlines()[-1].split(" ")[-2])

            stats['total'] += stats[repo]

        print(f"{i + 1}/{len(repos)} -- {stats[repo]['sloc'] if use_cloc else stats[repo]} "
              f"total non-blank lines in repo {repo}")

        if not (dev_mode and keep_repos):
            run(f"rm -rf {os.path.join('repos', repo)}".split())

    if not (dev_mode and keep_repos):
        run("rm -rf repos".split())

    return stats


def __generate_chart(data: dict, minimum: int, graph_type: str, legend: str, title: str, axis):
    keys = data.keys()
    values = data.values()
    count = len(values)

    total = 0
    labels = []

    for key in data:
        total += data[key]
    
    for key in data:
        percentage = (float(data[key] * 100) / float(total))
        labels.append('%s (%.2f%%)' % (key, percentage))

    if graph_type == 'pie':
        # Set the color map and generate a properly sized color cycle
        colors = []
        colormaps = {'Pastel1':9, 'Accent':8, 'Set1':9, 'tab20':20, 'tab20b':20}

        for cm in colormaps:
            cmap = plot.get_cmap(cm)
            colors += [cmap(i/colormaps[cm]) for i in range(colormaps[cm])]

        step = int(len(colors)/count)
        axis.set_prop_cycle('color', [colors[i*step] for i in range(count)])

        wedges, texts = axis.pie(values, counterclock=False, startangle=90)
        legend = axis.legend(wedges, labels, title=legend, bbox_to_anchor=(1.01, 1), loc='upper left')
        axis.set_aspect('equal')
        axis.set_title(f'{title} (total: {total})')

    elif graph_type == 'bar':
        y = [i for i in range(count)]

        bars = axis.barh(y, values, align='center')
        axis.set_yticks(y)
        axis.set_yticklabels(keys)
        axis.invert_yaxis()
        axis.set_xlabel(legend)
        axis.set_title(f'{title} (total: {total})')

        for bar in bars:
            width = bar.get_width()
            axis.annotate(str(width), xy=(width, bar.get_y() + bar.get_height() / 2), xytext=(3,0), textcoords='offset points', ha='left', va='center')


def _normalize_data(data: dict, min_value: float):
    # Remove summatory keys from the dictionary.
    # The additional 'nope' is there just to avoid having to put everything in a try in case the "total" key does not exist. 
    data.pop('total', 'nope')
    data.pop('past_year', 'nope')

    other = 0

    for key in list(data.keys()):
        if data[key] < min_value:
            other += data.pop(key)

    # Order data dictionary by size of elements
    data = {k:v for k,v in sorted(data.items(), key=lambda x: int(x[1]), reverse=True)}

    if other > 0:
        data['other'] = other
    
    return data


def generate_figure(graphs: List[Graph], path: str):
    filtered = sorted([graph for graph in graphs if graph.is_suitable()], key=lambda x: 0 if x.kind == 'pie' else 1)
    heights = []

    # If we have no suitable graphs, return without doing nothing
    if len(filtered) == 0:
        return

    for graph in filtered:
        if graph.kind == 'pie':
            heights.append(7)
        else:
            heights.append((0.3 * graph.count))

    figure, axis = plot.subplots(len(filtered),
                                 figsize=(12, sum(heights)),
                                 dpi=600,
                                 gridspec_kw={'height_ratios': [h / heights[0] for h in heights]})

    # We need a list for the following for loop and if len(filtered) = 1 axis is just an object. Maybe there is a better way to do this?
    if len(filtered) == 1:
        axis = [axis]

    for i,graph in enumerate(filtered):
        __generate_chart(graph.data, graph.minimum, graph.kind, graph.legend, graph.title, axis[i])
    
    plot.tight_layout()
    plot.savefig(path, bbox_inches='tight')
    plot.close(figure)


def _make_directory(path: str):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


def print_all_stats(commits_stats: dict, lines_stats: dict, contributors_stats: dict, use_cloc: bool, generate_graphs: bool):
    _make_directory(output_dir)

    if generate_graphs:
        print("Generating graphs...")

        timestamp = datetime.now().strftime("%Y-%m-%d %H.%M.%S.%f")
        graph_dir = os.path.join(output_dir, timestamp)
        _make_directory(graph_dir)
        _make_directory(os.path.join(graph_dir, owner))

        global_graphs = {}

        yearly_repo_commits = {}
        repo_commits = {}
        sloc_by_repo = {}

        if commits_stats is not None:
            yearly_commits_by_repo = Graph(dict(commits_stats), 10, 1, 'pie', 'Repositories', 'Commits in the last year by repository')
            global_graphs['yearly_commits_by_repo.svg'] = yearly_commits_by_repo

        if contributors_stats is not None:
            yearly_commits_by_contributor = Graph(dict(contributors_stats['past_year']), 1, 1, 'bar', 'Commits', 'Commits in the last year by contributor')
            commits_by_contributor = Graph(dict(contributors_stats['total']), 1, 1, 'bar', 'Commits', 'Commits by contributor')
            global_graphs['yearly_commits_by_contributor.svg'] = yearly_commits_by_contributor
            global_graphs['commits_by_contributor.svg'] = commits_by_contributor

            for repo in contributors_stats:
                if repo not in ['total', 'past_year']:
                    yearly_repo_commits[repo] = Graph(dict(contributors_stats[repo]['total']), 1, 2, 'bar', 'Commits', f'Commits to {owner}/{repo} by contributor')
                    repo_commits[repo] = Graph(dict(contributors_stats[repo]['past_year']), 1, 2, 'bar', 'Commits', f'Commits to {owner}/{repo} in the last year by contributor')

        if lines_stats is not None:
            if use_cloc:
                minimum = lines_stats['total']['sloc'] * 0.005
                total_sloc = Graph({r:lines_stats[r]['sloc'] for r in lines_stats if r != 'total'}, minimum, 1, 'pie', 'Repository', 'SLOC count by repository')
                global_graphs['sloc.svg'] = (total_sloc)

                for repo in lines_stats:
                    if repo != 'total':
                        sloc_by_repo[repo] = Graph(dict(lines_stats[repo]), 1, 1, 'pie', 'Type', f'Line distribution for repository {owner}/{repo}')

            else:
                total_sloc = Graph(dict(lines_stats), minimum, 1, 'pie', 'Repository', 'SLOC count by repository')
                global_graphs['sloc.svg'] = total_sloc

        for graph in sloc_by_repo:
            generate_figure([repo_commits[graph], yearly_repo_commits[graph], sloc_by_repo[graph]], os.path.join(graph_dir, f'{graph}.svg'))

        for graph in global_graphs:
            generate_figure([global_graphs[graph]], os.path.join(graph_dir, owner, graph))

        generate_figure(global_graphs.values(), os.path.join(graph_dir, owner, 'combined.svg'))

        # TODO: Generate all the other graphs

    if commits_stats is not None:
        commits_output = "\n".join([f"{repo}: {commits_stats[repo]} commits past year"
                                    for repo in commits_stats
                                    if repo != "total"])

        commits_output += f"\nTotal commits of past year: {commits_stats['total']}"
    else:
        commits_output = "No commits stats, as you've selected at the beginning."

    if contributors_stats is not None:
        # I know using replace like this is really bad, I just don't want to spend years parsing the output
        contributors_output = "\n".join([f"{repo}: {contributors_stats[repo]}"
                                         .replace("'", "")
                                         .replace(": {", "\n\t")
                                         .replace("}, ", "\n\t")
                                         .replace("}} ", "\n")
                                         .replace("}", "")
                                         .replace("total\n\t", "total:\n\t\t")
                                         .replace("past_year\n\t", "past year:\n\t\t")
                                         for repo in contributors_stats
                                         if repo not in ["total", "past_year"]])

        # sort by number of commits
        contributors_stats['total'] = {k: v for k, v in sorted(contributors_stats['total'].items(),
                                                               key=lambda item: item[1],
                                                               reverse=True)}

        contributors_stats['past_year'] = {k: v for k, v in sorted(contributors_stats['past_year'].items(),
                                                                   key=lambda item: item[1],
                                                                   reverse=True)}

        contributors_output += f"\nTotal all time:\n\t{contributors_stats['total']}" \
                               .replace("'", "") \
                               .replace(", ", "\n\t") \
                               .replace("{", "") \
                               .replace("}", "")
        contributors_output += f"\nPast year:\n\t{contributors_stats['past_year']}" \
                               .replace("'", "") \
                               .replace(", ", "\n\t") \
                               .replace("{", "") \
                               .replace("}", "")

    else:
        contributors_output = "No contributors stats, as you've selected at the beginning."

    if lines_stats is not None:
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
    else:
        lines_output = "No SLOC stats, as you've selected at the beginning."

    output = "\n\n".join([contributors_output, '*' * 42, commits_output, '*' * 42, lines_output])
    print(f"\n\n{output}")

    output_path = os.path.join(output_dir, f'{output_file} {datetime.now()}.txt') if not generate_graphs \
        else os.path.join(graph_dir, owner, f'{output_file}.txt')
    with open(output_path, 'w') as out:
        out.write(f"Stats generated via https://github.com/weee-open/sardina\n"
                  f"use_cloc={use_cloc}\n"
                  f"\n{output}")


def main():
    use_cloc = input("Do you want to use cloc (C) or wc (W) to count SLOC? c/W ").lower() == "c"
    get_commits = input("Do you want to get the commits stats? It may take a long time due to GitHub servers updating "
                        "their cache. y/N ").lower() == "y"
    get_lines = input("Do you want to get the SLOC stats? It may take a long time since it has to clone each repository. y/N ").lower() == "y"
    generate_graphs = input("Do you want to generate graphs for the statistics? y/N ").lower() == 'y'

    header = {'Authorization': f"token {token}"} if token != "YOUR TOKEN HERE" else {}

    repos = get_repos(header)
    commits_stats = get_anonymous_commits_stats(repos, header) if get_commits else None
    contributors_stats = get_contributors_commits_stats(repos, header) if get_commits else None
    lines_stats = get_lines_stats(repos, use_cloc) if get_lines else None
    print_all_stats(commits_stats, lines_stats, contributors_stats, use_cloc, generate_graphs)
    print(f"Done. You can see the results in the {output_dir} directory.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nQuitting...")
