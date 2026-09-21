"""Collect release-note source data for build123d with the GitHub CLI.

name: release_notes_data_gh.py
by:   Gumyr & Claude
date: September 17 2026

desc:

    A ``gh``-based counterpart of ``release_notes_data.py``. Local git is still
    the source of truth for commits and changed files; everything from GitHub
    comes through the ``gh`` command, which handles authentication, pagination
    and rate limits, so no token has to be managed here.

    Compared with the REST version, ``gh`` also supplies data that makes the
    notes easier to draft in the established style:

    * the issues each pull request closes (``closingIssuesReferences``);
    * the GitHub login of every commit author, so contributors can be listed
      as ``@login`` the way the published notes do;
    * GitHub's own generated notes for the range, whose "New Contributors"
      list is the one the published notes reproduce verbatim;
    * the body of the previous release(s), included as the style reference
      the drafting model must match.

    Typical usage:

        python tools/release_notes_data_gh.py \\
            --from-tag v0.11.1 \\
            --to-ref dev \\
            --version v0.12.0 \\
            --output release_data.json \\
            --summary-output release_summary.json \\
            --llm-input-output release_llm_input.json \\
            --github-notes-input-output release_github_notes_input.json

    Outputs match ``release_notes_data.py`` so existing drafting prompts keep
    working. ``release_github_notes_input.json`` is the one to hand to the
    model for the GitHub Releases page: it carries the previous release notes
    as ``style_reference``, an ``output_template`` describing every section of
    that format, GitHub's generated notes, the classified changes with links,
    compatibility candidates, and contributors by login.

    The change classification, summaries and topic grouping are imported from
    ``release_notes_data.py`` unchanged, so both tools rank and describe
    changes the same way.

license:

    Copyright 2026 Gumyr

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

# sibling module, found through sys.path
# pylint: disable=wrong-import-position
import release_notes_data as base  # noqa: E402
from release_notes_data import (  # noqa: E402
    ChangedFile,
    CommitRecord,
    IssueRecord,
    PullRequestRecord,
    ReleaseData,
    ReleaseRange,
    build_github_notes_input,
    build_llm_input,
    build_release_summary,
    collect_local_commits,
    compare_url,
    extract_commit_links,
    extract_number_refs,
    git_ref_date,
    git_ref_sha,
    git_remote_url,
    referenced_numbers_from_release_inputs,
)

DEFAULT_OWNER = base.DEFAULT_OWNER
DEFAULT_REPO = base.DEFAULT_REPO
DEFAULT_CACHE_DIR = Path(".cache/release-notes/gh")
GH_LIST_LIMIT = 1000

NEW_CONTRIBUTOR_RE = re.compile(
    r"^\* @(?P<login>[\w-]+) made their first contribution in (?P<url>\S+)"
)
WHATS_CHANGED_RE = re.compile(
    r"^\* (?P<title>.*) by @(?P<login>[\w-]+) in (?P<url>\S+/pull/(?P<number>\d+))$"
)


# ---------------------------------------------------------------------------
# gh transport
# ---------------------------------------------------------------------------


class GhError(RuntimeError):
    """A gh command failed."""


class Gh:
    """Runs ``gh`` and caches its JSON output by command line."""

    def __init__(self, cache_dir: Path | None):
        if shutil.which("gh") is None:
            raise GhError("the GitHub CLI 'gh' is not installed or not on PATH")
        self.cache_dir = cache_dir
        self.calls = 0

    def json(self, *args: str, cacheable: bool = True) -> Any:
        """Run a gh command that prints JSON and return the parsed value."""
        key = sha256("\x1f".join(args).encode()).hexdigest()
        cache_file = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if cacheable and cache_file is not None and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))
        text = self.text(*args)
        value = json.loads(text) if text.strip() else None
        if cacheable and cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(value), encoding="utf-8")
        return value

    def text(self, *args: str) -> str:
        """Run a gh command and return its stdout."""
        self.calls += 1
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise GhError(f"gh {' '.join(args[:3])} ... failed: {detail}")
        return result.stdout


def check_gh_auth(gh: Gh) -> str:
    """The login gh is authenticated as; raises with gh's own message if not."""
    try:
        return gh.text("api", "user", "--jq", ".login").strip()
    except GhError as err:
        raise GhError(
            f"{err}\nRun 'gh auth login' (or fix GITHUB_TOKEN, which gh prefers "
            "when it is set) and try again."
        ) from err


# ---------------------------------------------------------------------------
# GitHub data through gh
# ---------------------------------------------------------------------------


def github_date(date_text: str) -> str:
    """The YYYY-MM-DD part of an ISO date, as gh search filters want it."""
    return date_text[:10]


def in_range(when: str | None, from_date: str, to_date: str) -> bool:
    """Is an ISO timestamp after from_date and up to to_date?"""
    if not when:
        return False
    moment = datetime.fromisoformat(when.replace("Z", "+00:00"))
    return datetime.fromisoformat(from_date) < moment <= datetime.fromisoformat(to_date)


def changed_files_from_gh(files: list[dict[str, Any]] | None) -> list[ChangedFile]:
    """Per-file stats as gh reports them for a pull request."""
    return [
        ChangedFile(
            path=file.get("path", ""),
            additions=file.get("additions"),
            deletions=file.get("deletions"),
        )
        for file in files or []
    ]


def collect_merged_pull_requests(
    gh: Gh,
    owner: str,
    repo: str,
    release: ReleaseRange,
    commit_shas: set[str],
    include_files: bool,
) -> tuple[list[PullRequestRecord], dict[int, list[int]]]:
    """Merged pull requests in the range, and the issues each one closes.

    A pull request belongs to the release when its merge commit is one of the
    local commits in the range; pull requests merged in the date window whose
    merge commit is not in the range (another branch) are left out.
    """
    fields = [
        "number",
        "title",
        "body",
        "state",
        "author",
        "url",
        "createdAt",
        "updatedAt",
        "mergedAt",
        "mergeCommit",
        "changedFiles",
        "labels",
        "additions",
        "deletions",
        "closingIssuesReferences",
        "baseRefName",
    ]
    if include_files:
        fields.append("files")
    search = f"merged:{github_date(release.from_date)}..{github_date(release.to_date)}"
    items = gh.json(
        "pr",
        "list",
        "--repo",
        f"{owner}/{repo}",
        "--state",
        "merged",
        "--search",
        search,
        "--limit",
        str(GH_LIST_LIMIT),
        "--json",
        ",".join(fields),
    )
    pull_requests: list[PullRequestRecord] = []
    linked_issues: dict[int, list[int]] = {}
    skipped = 0
    for item in items:
        merge_sha = (item.get("mergeCommit") or {}).get("oid")
        if merge_sha not in commit_shas:
            skipped += 1
            continue
        title = item.get("title") or ""
        body = item.get("body") or ""
        author = item.get("author") or {}
        pull_requests.append(
            PullRequestRecord(
                number=item["number"],
                title=title,
                body=body,
                state=str(item.get("state", "")).lower(),
                user_login=author.get("login"),
                html_url=item.get("url", ""),
                created_at=item.get("createdAt", ""),
                updated_at=item.get("updatedAt", ""),
                merged_at=item.get("mergedAt", ""),
                merge_commit_sha=merge_sha,
                changed_file_count=item.get("changedFiles", 0),
                labels=[label.get("name", "") for label in item.get("labels", [])],
                changed_files=changed_files_from_gh(item.get("files")),
                additions=item.get("additions", 0),
                deletions=item.get("deletions", 0),
                referenced_numbers=extract_number_refs(f"{title}\n{body}"),
            )
        )
        linked_issues[item["number"]] = sorted(
            ref["number"] for ref in item.get("closingIssuesReferences") or []
        )
    pull_requests.sort(key=lambda pr: pr.merged_at)
    print(
        f"{len(pull_requests)} merged PRs in range"
        + (f" ({skipped} merged elsewhere in the date window)" if skipped else ""),
        file=sys.stderr,
    )
    return pull_requests, linked_issues


def collect_closed_issue_numbers(
    gh: Gh, owner: str, repo: str, release: ReleaseRange
) -> set[int]:
    """Issue numbers closed within the release date range."""
    search = f"closed:{github_date(release.from_date)}..{github_date(release.to_date)}"
    items = gh.json(
        "issue",
        "list",
        "--repo",
        f"{owner}/{repo}",
        "--state",
        "closed",
        "--search",
        search,
        "--limit",
        str(GH_LIST_LIMIT),
        "--json",
        "number,closedAt",
    )
    return {
        item["number"]
        for item in items
        if in_range(item.get("closedAt"), release.from_date, release.to_date)
    }


def fetch_issue(
    gh: Gh,
    owner: str,
    repo: str,
    number: int,
    source: set[str],
    referenced_by: set[str],
    commits_by_sha: dict[str, CommitRecord],
    include_comments: bool,
) -> IssueRecord:
    """One issue, or a pull request seen as an issue, through the REST API.

    ``gh api`` is used rather than ``gh issue view`` because the latter
    refuses pull request numbers, and commit messages reference both.
    """
    issue = gh.json("api", f"repos/{owner}/{repo}/issues/{number}")
    body = issue.get("body") or ""
    comments: list[str] = []
    if include_comments and issue.get("comments"):
        comments = [
            comment.get("body") or ""
            for comment in gh.json(
                "api", "--paginate", f"repos/{owner}/{repo}/issues/{number}/comments"
            )
            or []
        ]
    linked_commits = extract_commit_links("\n".join([body, *comments]), commits_by_sha)
    for sha in linked_commits:
        referenced_by.add(f"commit:{commits_by_sha[sha].short_sha}")
    user = issue.get("user") or {}
    return IssueRecord(
        number=issue.get("number"),
        title=issue.get("title") or "",
        body=body,
        state=issue.get("state", ""),
        user_login=user.get("login"),
        html_url=issue.get("html_url", ""),
        created_at=issue.get("created_at", ""),
        updated_at=issue.get("updated_at", ""),
        closed_at=issue.get("closed_at"),
        labels=[label.get("name", "") for label in issue.get("labels", [])],
        is_pull_request="pull_request" in issue,
        source=sorted(source),
        referenced_by=sorted(referenced_by),
        linked_commits=linked_commits,
    )


def collect_issues(
    gh: Gh,
    owner: str,
    repo: str,
    release: ReleaseRange,
    commits: list[CommitRecord],
    pull_requests: list[PullRequestRecord],
    linked_issues: dict[int, list[int]],
    include_comments: bool,
) -> list[IssueRecord]:
    """Issues referenced by commits or PRs, linked to PRs, or closed in range."""
    commits_by_sha = {commit.sha: commit for commit in commits}
    referenced = referenced_numbers_from_release_inputs(commits, pull_requests)
    sources: dict[int, set[str]] = {number: {"referenced"} for number in referenced}
    references: dict[int, set[str]] = {
        number: set(refs) for number, refs in referenced.items()
    }
    for pr_number, numbers in linked_issues.items():
        for number in numbers:
            sources.setdefault(number, set()).add("linked_to_pr")
            references.setdefault(number, set()).add(f"pr:{pr_number}")
    closed = collect_closed_issue_numbers(gh, owner, repo, release)
    for number in closed:
        sources.setdefault(number, set()).add("closed_in_range")
        references.setdefault(number, set())
    print(
        f"fetching {len(sources)} issues/PR-number references "
        f"({len(closed)} closed issues)",
        file=sys.stderr,
    )
    issues: list[IssueRecord] = []
    for number in sorted(sources):
        try:
            issues.append(
                fetch_issue(
                    gh,
                    owner,
                    repo,
                    number,
                    sources[number],
                    references[number],
                    commits_by_sha,
                    include_comments,
                )
            )
        except GhError as err:
            print(f"warning: could not fetch #{number}: {err}", file=sys.stderr)
    return issues


def commit_author_logins(
    gh: Gh, owner: str, repo: str, release: ReleaseRange
) -> dict[str, str]:
    """GitHub login for every commit sha in the range, from the compare API.

    One paginated call instead of one per commit; commits whose author has no
    GitHub account (unknown email) are absent from the result.
    """
    pages = gh.json(
        "api",
        "--paginate",
        "--slurp",
        f"repos/{owner}/{repo}/compare/{release.from_sha}...{release.to_sha}",
    )
    logins: dict[str, str] = {}
    for page in pages or []:
        for commit in page.get("commits", []):
            author = commit.get("author") or {}
            if author.get("login"):
                logins[commit["sha"]] = author["login"]
    return logins


def generated_notes(
    gh: Gh, owner: str, repo: str, version: str, from_ref: str, to_sha: str
) -> dict[str, Any]:
    """GitHub's own generated release notes for the range, parsed."""
    body = gh.json(
        "api",
        f"repos/{owner}/{repo}/releases/generate-notes",
        "-f",
        f"tag_name={version}",
        "-f",
        f"previous_tag_name={from_ref}",
        "-f",
        f"target_commitish={to_sha}",
    ).get("body", "")
    whats_changed = []
    new_contributors = []
    for line in body.splitlines():
        match = WHATS_CHANGED_RE.match(line.strip())
        if match:
            whats_changed.append(
                {
                    "number": int(match["number"]),
                    "title": match["title"],
                    "login": match["login"],
                    "url": match["url"],
                    "line": line.strip(),
                }
            )
        match = NEW_CONTRIBUTOR_RE.match(line.strip())
        if match:
            new_contributors.append(
                {"login": match["login"], "url": match["url"], "line": line.strip()}
            )
    return {
        "body": body,
        "whats_changed": whats_changed,
        "new_contributors": new_contributors,
    }


def previous_releases(
    gh: Gh, owner: str, repo: str, count: int
) -> list[dict[str, Any]]:
    """The bodies of the most recent published releases, newest first."""
    releases = gh.json(
        "release",
        "list",
        "--repo",
        f"{owner}/{repo}",
        "--exclude-drafts",
        "--exclude-pre-releases",
        "--limit",
        str(count),
        "--json",
        "tagName,name,publishedAt",
    )
    result = []
    for release in releases or []:
        tag = release["tagName"]
        body = gh.json(
            "release", "view", tag, "--repo", f"{owner}/{repo}", "--json", "body"
        )["body"].replace("\r\n", "\n")
        result.append(
            {
                "tag": tag,
                "name": release.get("name"),
                "published_at": release.get("publishedAt"),
                "sections": re.findall(r"^## (.+)$", body, flags=re.M),
                "body": body,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def collect_release_data(
    gh: Gh,
    owner: str,
    repo: str,
    from_ref: str,
    to_ref: str,
    include_pr_files: bool,
    include_issue_comments: bool,
) -> tuple[ReleaseData, dict[int, list[int]]]:
    """Local commits plus the GitHub data reachable from them."""
    release = ReleaseRange(
        repo=git_remote_url(),
        from_ref=from_ref,
        from_sha=git_ref_sha(from_ref),
        from_date=git_ref_date(from_ref),
        to_ref=to_ref,
        to_sha=git_ref_sha(to_ref),
        to_date=git_ref_date(to_ref),
    )
    commits = collect_local_commits(from_ref, to_ref)
    print(f"{len(commits)} local commits in {from_ref}..{to_ref}", file=sys.stderr)
    pull_requests, linked_issues = collect_merged_pull_requests(
        gh, owner, repo, release, {commit.sha for commit in commits}, include_pr_files
    )
    issues = collect_issues(
        gh,
        owner,
        repo,
        release,
        commits,
        pull_requests,
        linked_issues,
        include_issue_comments,
    )
    return ReleaseData(release, commits, pull_requests, issues), linked_issues


def contributors_by_login(
    data: ReleaseData, logins: dict[str, str], generated: dict[str, Any]
) -> dict[str, Any]:
    """Everyone who contributed, keyed by GitHub login where one is known."""
    people: dict[str, dict[str, Any]] = {}
    unresolved: dict[str, dict[str, Any]] = {}
    for commit in data.commits:
        login = logins.get(commit.sha)
        if login:
            entry = people.setdefault(
                login,
                {
                    "login": login,
                    "name": commit.author.name,
                    "commits": 0,
                    "pull_requests": 0,
                },
            )
            entry["commits"] += 1
        else:
            key = base.person_key(commit.author.name, commit.author.email)
            entry = unresolved.setdefault(
                key,
                {
                    "name": commit.author.name,
                    "email": commit.author.email,
                    "commits": 0,
                },
            )
            entry["commits"] += 1
    for pull_request in data.pull_requests:
        login = pull_request.user_login
        if login:
            entry = people.setdefault(
                login, {"login": login, "name": None, "commits": 0, "pull_requests": 0}
            )
            entry["pull_requests"] += 1
    first_time = {item["login"] for item in generated["new_contributors"]}
    for login, entry in people.items():
        entry["first_time"] = login in first_time
    ordered = sorted(people.values(), key=lambda entry: entry["login"].casefold())
    return {
        "all": ordered,
        "first_time": generated["new_contributors"],
        "unresolved_git_authors": sorted(
            unresolved.values(), key=lambda entry: str(entry["name"]).casefold()
        ),
        "markdown_list": ", ".join(
            f"[@{entry['login']}](https://github.com/{entry['login']})"
            for entry in ordered
        ),
    }


def output_template(previous: list[dict[str, Any]]) -> dict[str, Any]:
    """The section layout of the published notes, as observed in them."""
    return {
        "title": "{version}",
        "note": (
            "The release title is the bare tag, e.g. 'v0.12.0'. Section headings "
            "are '## ' level. Reproduce the section order below; omit optional "
            "sections that have nothing to say."
        ),
        "sections": [
            {
                "heading": "Breaking Changes",
                "optional": True,
                "instructions": (
                    "Only confirmed backwards-incompatible changes, each a bullet "
                    "with enough explanation for a user to act on, linking the "
                    "tracking issue or PR."
                ),
            },
            {
                "heading": "Compatibility Notes",
                "optional": True,
                "intro": (
                    "These are compatibility-related changes that users should "
                    "review. They are not necessarily all breaking changes."
                ),
                "instructions": (
                    "Deprecations, moved or renamed APIs, changed defaults and "
                    "behaviour changes. One bullet each, ending 'by @login in "
                    "[#N](url).' for a PR or 'in [shortsha](url).' for a commit."
                ),
            },
            {
                "heading": "Notable Changes",
                "instructions": (
                    "8 to 20 bullets for the user-visible features and larger "
                    "improvements, most important first. Each bullet names the "
                    "change with backticked API names, then the credit: 'by "
                    "@login in [#N](url)' or 'in [shortsha](url)', 'and related "
                    "commits' when several. Group related PRs and commits into "
                    "one bullet."
                ),
            },
            {
                "heading": "Selected Other Changes",
                "instructions": (
                    "Smaller fixes, docs and tooling, one bullet per PR or "
                    "commit, in PR-number order, same credit form. Include every "
                    "merged PR from an outside contributor; commit-only changes "
                    "may be left out when minor."
                ),
            },
            {
                "heading": "New Contributors",
                "optional": True,
                "intro": "Thanks to the following first-time contributors:",
                "instructions": (
                    "Copy generated_notes.new_contributors lines verbatim: "
                    "'* @login made their first contribution in <PR url>'."
                ),
            },
            {
                "heading": "Contributors",
                "intro": "Thanks to everyone who contributed to this release:",
                "instructions": (
                    "One paragraph: contributors.markdown_list, alphabetical, "
                    "comma separated, 'and' before the last, ending with a period."
                ),
            },
            {
                "heading": "Full Changelog",
                "instructions": (
                    "'**Full Changelog**: <release.full_changelog_url>' with the "
                    "real tags, e.g. compare/v0.11.1...v0.12.0."
                ),
            },
        ],
        "observed_in_previous_releases": {
            release["tag"]: release["sections"] for release in previous
        },
    }


STYLE_GUIDE = [
    "Match the previous release bodies in style_reference exactly: headings, "
    "bullet form, credit form, section intros and closing period on bullets.",
    "Bullets start with a verb in the past tense: Added, Fixed, Improved, Changed.",
    "Put API names in backticks; link PRs as [#N](url) and commits as [shortsha](url).",
    "Credit the PR author with 'by @login'; for commits with no PR use the commit "
    "author's login when known, otherwise no credit.",
    "Do not invent changes, logins or links; every bullet must trace to an entry "
    "in selected_other_changes, notable_topics or compatibility_candidates.",
    "Do not include every commit; internal refactors and CI-only changes belong "
    "in Selected Other Changes only when a user would notice them.",
]


def build_gh_notes_input(
    data: ReleaseData,
    summary: dict[str, Any],
    owner: str,
    repo: str,
    version: str,
    linked_issues: dict[int, list[int]],
    logins: dict[str, str],
    generated: dict[str, Any],
    previous: list[dict[str, Any]],
) -> dict[str, Any]:
    """The GitHub-style drafting input, extended with the gh-only data."""
    notes_input = build_github_notes_input(data, summary, owner, repo)
    notes_input["release"] = {
        **notes_input["release"],
        "version": version,
        "full_changelog_url": compare_url(owner, repo, data.release.from_ref, version),
    }
    notes_input["output_template"] = output_template(previous)
    notes_input["style_guide"] = STYLE_GUIDE
    notes_input["style_reference"] = previous
    notes_input["generated_notes"] = generated
    notes_input["contributors"] = contributors_by_login(data, logins, generated)
    notes_input["new_contributors"] = generated["new_contributors"]
    notes_input["pull_request_linked_issues"] = {
        str(number): issues for number, issues in linked_issues.items() if issues
    }
    notes_input["commit_author_logins"] = {
        sha[:8]: login for sha, login in logins.items()
    }
    notes_input["llm_instructions"] = [
        "Generate Markdown for the GitHub release body only, no preamble.",
        "Follow output_template section order and wording; match style_reference.",
        "Use notable_topics and selected_other_changes for the change bullets; "
        "pull_request_linked_issues says which issues a PR fixed.",
        "Use compatibility_candidates for Compatibility Notes; claim a Breaking "
        "Change only when the entry is clearly breaking.",
        "Copy generated_notes.new_contributors verbatim into New Contributors.",
        "Use contributors.markdown_list for the Contributors paragraph.",
        "End with the Full Changelog line using release.full_changelog_url.",
    ]
    notes_input["counts"] = {
        **notes_input["counts"],
        "generated_whats_changed": len(generated["whats_changed"]),
        "new_contributors": len(generated["new_contributors"]),
        "contributors": len(notes_input["contributors"]["all"]),
    }
    return notes_input


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect build123d release-note data with the GitHub CLI."
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--from-tag",
        "--from-ref",
        dest="from_ref",
        required=True,
        help="The previous release tag, e.g. v0.11.1.",
    )
    parser.add_argument(
        "--to-ref", default="HEAD", help="Collect up to this ref. Defaults to HEAD."
    )
    parser.add_argument(
        "--version",
        help="The tag the notes are for, e.g. v0.12.0. Used for the generated "
        "notes and the Full Changelog link. Defaults to --to-ref when it is a tag.",
    )
    parser.add_argument("--output", type=Path, help="Full audit data JSON.")
    parser.add_argument("--summary-output", type=Path, help="Condensed summary JSON.")
    parser.add_argument(
        "--llm-input-output", type=Path, help="Grouped topics JSON for drafting."
    )
    parser.add_argument(
        "--github-notes-input-output",
        type=Path,
        help="GitHub-release-style drafting input JSON (the one to use).",
    )
    parser.add_argument(
        "--include-pr-files",
        action="store_true",
        help="Include per-file PR details (gh returns them with the PR list).",
    )
    parser.add_argument(
        "--skip-issue-comments",
        action="store_true",
        help="Do not fetch issue comments (one gh call per commented issue).",
    )
    parser.add_argument(
        "--previous-releases",
        type=int,
        default=2,
        help="How many previous release bodies to include as the style reference.",
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--no-cache", action="store_true")
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    version = args.version or (
        args.to_ref if re.match(r"^v\d+\.\d+", args.to_ref) else "vNEXT"
    )
    try:
        gh = Gh(None if args.no_cache else args.cache_dir)
        login = check_gh_auth(gh)
        print(f"gh authenticated as {login}", file=sys.stderr)
        data, linked_issues = collect_release_data(
            gh,
            args.owner,
            args.repo,
            args.from_ref,
            args.to_ref,
            args.include_pr_files,
            not args.skip_issue_comments,
        )
        logins = commit_author_logins(gh, args.owner, args.repo, data.release)
        generated = generated_notes(
            gh, args.owner, args.repo, version, args.from_ref, data.release.to_sha
        )
        previous = previous_releases(gh, args.owner, args.repo, args.previous_releases)
    except (GhError, subprocess.CalledProcessError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    summary = build_release_summary(data)
    llm_input = build_llm_input(summary)
    notes_input = build_gh_notes_input(
        data,
        summary,
        args.owner,
        args.repo,
        version,
        linked_issues,
        logins,
        generated,
        previous,
    )

    outputs = [
        (
            args.output,
            asdict(data),
            f"{len(data.commits)} commits, "
            f"{len(data.pull_requests)} PRs, {len(data.issues)} issues",
        ),
        (
            args.summary_output,
            summary,
            f"{summary['counts']['release_note_candidates']} candidates",
        ),
        (
            args.llm_input_output,
            llm_input,
            f"{llm_input['counts']['llm_topics']} topics",
        ),
        (
            args.github_notes_input_output,
            notes_input,
            f"{notes_input['counts']['selected_other_changes']} selected changes, "
            f"{notes_input['counts']['new_contributors']} new contributors, "
            f"{len(previous)} previous release bodies",
        ),
    ]
    written = False
    for path, value, note in outputs:
        if path is None:
            continue
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {note} to {path}", file=sys.stderr)
        written = True
    if not written:
        print(json.dumps(notes_input, indent=2))
    print(f"{gh.calls} gh calls", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
