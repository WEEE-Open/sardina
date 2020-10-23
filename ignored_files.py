# These are Python regular expressions, treat them as such
# WARNING: Do not use the start anchor (^) in your expressions
#          as the path that these expressions are evaluated against
#          is a relative path to the script directory,
#          so they will all be in the form:
#
#          repos/<repo_name>/file/path/
#
#          This is by design since cloc just works this way.
ignored_files = [
    "^.*\.txt$",
    "^.*\.md$",
    "^.*\.xml$",
    "^.*\.svg$",
    "^LICENSE$",
    "^\.git.*",
    "^.*\.min\.js$",
    "^.*\.min\.css$",
    "^composer\.json$",
    "^composer\.lock$",
    "^Pipfile$",
    "^Pipfile\.lock$",
    "^bootstrap-dark.css$"
]