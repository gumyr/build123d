"""Collect release-note source data for build123d.

name: release_notes_data.py
by:   Gumyr & Codex
date: June 8 2026

desc:

    The tool combines local git history with GitHub metadata to produce structured
    inputs for release-note drafting. Local git is the source of truth for commits
    and changed files; GitHub is used to enrich the data with merged PRs, linked or
    closed issues, labels, issue comments, and contributor-facing metadata.

    Typical usage:

        python tools/release_notes_data.py \
            --from-tag v0.10.0 \
            --to-ref HEAD \
            --output release_data.json \
            --summary-output release_summary.json \
            --llm-input-output release_llm_input.json \
            --github-notes-input-output release_github_notes_input.json

    Outputs:

    * ``--output`` writes the full audit data: commits, PRs, and issues.
    * ``--summary-output`` writes a condensed but still broad release summary.
    * ``--llm-input-output`` writes grouped topics intended for LLM drafting.
    * ``--github-notes-input-output`` writes a single LLM input tailored to the
      existing GitHub release-note style, including a template, style guide,
      linked selected changes, compatibility candidates, contributors, and the
      full changelog URL.

    Drafting release notes with an LLM:

    Use ``release_github_notes_input.json`` when drafting release notes for the
    GitHub Releases page in the existing project style. This file includes a
    template, style guide, linked PR/commit entries, compatibility candidates,
    contributor data, and the full changelog URL. Use ``release_llm_input.json``
    for a shorter grouped/editorial draft. In either case, ask the LLM to merge
    related topics instead of producing one bullet per topic, include a
    Compatibility Notes section from ``compatibility_candidates``, and treat the
    generated Markdown as a review draft; verify compatibility notes and contributor
    names before publishing.

    Authentication:

    Set ``GITHUB_TOKEN`` in the environment before running authenticated GitHub
    queries. The token is only sent in the Authorization header and is never written
    to output files or cache entries. The GitHub response cache keys are derived
    from API paths, not credentials.

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
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_OWNER = "gumyr"
DEFAULT_REPO = "build123d"
GITHUB_API = "https://api.github.com"
DEFAULT_CACHE_DIR = Path(".cache/release-notes/github")


@dataclass(frozen=True)
class CommitSample:
    """Minimal commit metadata used to verify GitHub API access."""

    sha: str
    html_url: str
    author_name: str | None
    author_login: str | None
    date: str | None
    message_headline: str


@dataclass(frozen=True)
class GitPerson:
    """A person recorded in local git metadata."""

    name: str
    email: str


@dataclass(frozen=True)
class ChangedFile:
    """Per-file diff stats for one commit."""

    path: str
    additions: int | None
    deletions: int | None


@dataclass(frozen=True)
class CommitRecord:
    """Local git commit metadata for release notes."""

    sha: str
    short_sha: str
    parents: list[str]
    author: GitPerson
    author_date: str
    committer: GitPerson
    committer_date: str
    title: str
    body: str
    changed_files: list[ChangedFile]
    additions: int
    deletions: int
    referenced_issues: list[int]
    referenced_prs: list[int]
    is_merge: bool


@dataclass(frozen=True)
class PullRequestRecord:
    """GitHub pull request metadata for release notes."""

    number: int
    title: str
    body: str
    state: str
    user_login: str | None
    html_url: str
    created_at: str
    updated_at: str
    merged_at: str
    merge_commit_sha: str | None
    changed_file_count: int
    labels: list[str]
    changed_files: list[ChangedFile]
    additions: int
    deletions: int
    referenced_numbers: list[int]


@dataclass(frozen=True)
class IssueRecord:
    """GitHub issue metadata for release notes."""

    number: int
    title: str
    body: str
    state: str
    user_login: str | None
    html_url: str
    created_at: str
    updated_at: str
    closed_at: str | None
    labels: list[str]
    is_pull_request: bool
    source: list[str]
    referenced_by: list[str]
    linked_commits: list[str]


@dataclass(frozen=True)
class ReleaseRange:
    """Resolved release range metadata."""

    repo: str
    from_ref: str
    from_sha: str
    from_date: str
    to_ref: str
    to_sha: str
    to_date: str


@dataclass(frozen=True)
class ReleaseData:
    """Structured release data collected so far."""

    release: ReleaseRange
    commits: list[CommitRecord]
    pull_requests: list[PullRequestRecord]
    issues: list[IssueRecord]


SUMMARY_CATEGORIES = (
    "features",
    "bug_fixes",
    "documentation",
    "maintenance",
    "internal",
    "uncategorized",
)
LOW_VALUE_PATTERNS = (
    "appease mypy",
    "black",
    "cleanup",
    "coverage",
    "format",
    "lint",
    "mypy",
    "pylint",
    "typing",
    "typo",
)
TOPIC_LIMITS = {
    "features": 35,
    "bug_fixes": 35,
    "documentation": 18,
    "maintenance": 10,
    "uncategorized": 12,
}
COMPATIBILITY_PATTERNS = (
    ("deprecation", re.compile(r"deprecat", re.I)),
    ("removal", re.compile(r"\bremove[ds]?\b|\bremoved\b", re.I)),
    (
        "replacement_or_move",
        re.compile(r"\breplace[ds]?\b|\bmoved?\b|move .* to ", re.I),
    ),
    (
        "default_behavior",
        re.compile(r"\bdefault\b.*\bchange|\bchange\b.*\bdefault\b", re.I),
    ),
    (
        "signature_or_keyword",
        re.compile(r"\bkwarg\b|\bkeyword\b|constructor|signature", re.I),
    ),
    (
        "return_type",
        re.compile(r"return type|returns? .*ShapeList|return .*ShapeList", re.I),
    ),
    ("read_only", re.compile(r"read-only|readonly", re.I)),
)


ISSUE_OR_PR_RE = re.compile(
    r"(?<![\w/])#(?P<hash_number>\d+)\b"
    r"|github\.com/[^/\s]+/[^/\s]+/(?:issues|pull)/(?P<url_number>\d+)\b"
)
COMMIT_URL_RE = re.compile(
    r"github\.com/[^/\s]+/[^/\s]+/commit/(?P<sha>[0-9a-fA-F]{7,40})\b"
)
SHA_RE = re.compile(r"(?<![0-9a-fA-F])(?P<sha>[0-9a-fA-F]{12,40})(?![0-9a-fA-F])")


def run_git(args: list[str]) -> str:
    """Run git and return stdout."""
    completed = subprocess.run(
        ["git", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def git_ref_sha(ref: str) -> str:
    """Resolve a git ref to a commit SHA."""
    return run_git(["rev-parse", ref]).strip()


def git_ref_date(ref: str) -> str:
    """Return the committer date for a git ref."""
    return run_git(["show", "-s", "--format=%cI", ref]).strip()


def git_remote_url() -> str:
    """Return the origin URL if available."""
    try:
        return run_git(["remote", "get-url", "origin"]).strip()
    except subprocess.CalledProcessError:
        return ""


def extract_number_refs(text: str) -> list[int]:
    """Extract GitHub-style #number references from text."""
    numbers = set()
    for match in ISSUE_OR_PR_RE.finditer(text):
        number = match.group("hash_number") or match.group("url_number")
        if number:
            numbers.add(int(number))
    return sorted(numbers)


def resolve_commit_sha_prefix(
    prefix: str, commits_by_sha: dict[str, CommitRecord]
) -> str | None:
    """Resolve a SHA or unique SHA prefix to a local release commit SHA."""
    prefix = prefix.lower()
    matches = [sha for sha in commits_by_sha if sha.lower().startswith(prefix)]
    return matches[0] if len(matches) == 1 else None


def extract_commit_links(
    text: str,
    commits_by_sha: dict[str, CommitRecord],
) -> list[str]:
    """Extract commit URLs/raw SHAs that match local release commits."""
    linked_commits = set()
    for match in COMMIT_URL_RE.finditer(text):
        sha = resolve_commit_sha_prefix(match.group("sha"), commits_by_sha)
        if sha:
            linked_commits.add(sha)
    for match in SHA_RE.finditer(text):
        sha = resolve_commit_sha_prefix(match.group("sha"), commits_by_sha)
        if sha:
            linked_commits.add(sha)
    return sorted(linked_commits)


def referenced_numbers_from_release_inputs(
    commits: list[CommitRecord],
    pull_requests: list[PullRequestRecord],
) -> dict[int, set[str]]:
    """Map referenced GitHub numbers to commit/PR source IDs."""
    references: dict[int, set[str]] = defaultdict(set)
    for commit in commits:
        for number in commit.referenced_issues:
            references[number].add(f"commit:{commit.short_sha}")
    for pull_request in pull_requests:
        for number in pull_request.referenced_numbers:
            references[number].add(f"pr:{pull_request.number}")
    return references


def commit_changed_files(sha: str) -> list[ChangedFile]:
    """Collect per-file numstat data for a commit."""
    files: list[ChangedFile] = []
    output = run_git(["show", "--format=", "--numstat", "--find-renames", sha])
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        additions_text, deletions_text, path = parts[0], parts[1], parts[-1]
        additions = None if additions_text == "-" else int(additions_text)
        deletions = None if deletions_text == "-" else int(deletions_text)
        files.append(ChangedFile(path=path, additions=additions, deletions=deletions))
    return files


def collect_local_commits(from_ref: str, to_ref: str) -> list[CommitRecord]:
    """Collect commits in a local git range."""
    range_spec = f"{from_ref}..{to_ref}"
    output = run_git(
        [
            "log",
            "--reverse",
            "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%cn%x1f%ce%x1f%cI%x1f%s%x1f%b%x1e",
            range_spec,
        ]
    )

    commits: list[CommitRecord] = []
    for record in output.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        fields = record.split("\x1f")
        if len(fields) != 10:
            raise RuntimeError(
                f"Unexpected git log record with {len(fields)} fields for {fields[0]}"
            )
        (
            sha,
            parents_text,
            author_name,
            author_email,
            author_date,
            committer_name,
            committer_email,
            committer_date,
            title,
            body,
        ) = fields
        parents = parents_text.split() if parents_text else []
        changed_files = commit_changed_files(sha)
        referenced_numbers = extract_number_refs(f"{title}\n{body}")
        commits.append(
            CommitRecord(
                sha=sha,
                short_sha=sha[:8],
                parents=parents,
                author=GitPerson(author_name, author_email),
                author_date=author_date,
                committer=GitPerson(committer_name, committer_email),
                committer_date=committer_date,
                title=title,
                body=body.strip(),
                changed_files=changed_files,
                additions=sum(file.additions or 0 for file in changed_files),
                deletions=sum(file.deletions or 0 for file in changed_files),
                referenced_issues=referenced_numbers,
                referenced_prs=referenced_numbers if "(#" in title else [],
                is_merge=len(parents) > 1,
            )
        )
    return commits


def collect_release_data(
    owner: str,
    repo: str,
    from_ref: str,
    to_ref: str,
    token: str | None,
    include_pr_files: bool,
    include_issue_comments: bool,
    cache_dir: Path | None,
) -> ReleaseData:
    """Collect the local-git portion of release data."""
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
    pull_requests = collect_merged_pull_requests(
        owner,
        repo,
        release.from_date,
        release.to_date,
        token,
        include_pr_files,
        cache_dir,
    )
    return ReleaseData(
        release=release,
        commits=commits,
        pull_requests=pull_requests,
        issues=collect_issues(
            owner,
            repo,
            release,
            commits,
            pull_requests,
            token,
            include_issue_comments,
            cache_dir,
        ),
    )


def person_key(name: str, email: str | None = None) -> str:
    """Normalize a person identity for local contributor comparison."""
    return f"{name.strip().casefold()} <{(email or '').strip().casefold()}>"


def previous_git_contributors(from_ref: str) -> set[str]:
    """Return local git contributors before the release range."""
    contributors = set()
    output = run_git(["log", "--format=%an%x1f%ae", from_ref])
    for line in output.splitlines():
        if not line:
            continue
        name, email = line.split("\x1f", maxsplit=1)
        contributors.add(person_key(name, email))
    return contributors


def truncate_text(text: str, limit: int = 1200) -> str:
    """Trim long text fields for LLM-friendly summaries."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3].rstrip()}..."


def changed_paths(changed_files: list[ChangedFile]) -> list[str]:
    """Return changed paths from a commit/PR."""
    return [changed_file.path for changed_file in changed_files]


def classify_change(
    title: str,
    body: str,
    labels: list[str],
    paths: list[str],
) -> str:
    """Classify a change for release-note grouping."""
    text = f"{title}\n{body}".casefold()
    label_text = " ".join(labels).casefold()

    if paths and all(
        path.startswith(("docs/", "README", "examples/")) for path in paths
    ):
        return "documentation"
    if any(word in text for word in ("docs", "readme", "tutorial", "example")):
        return "documentation"
    if "bug" in label_text or any(
        word in text
        for word in (
            "bug",
            "correct",
            "fix",
            "fixed",
            "fixes",
            "handle",
            "regression",
            "resolve",
            "resolved",
        )
    ):
        return "bug_fixes"
    if "enhancement" in label_text or any(
        word in text
        for word in (
            "add ",
            "added",
            "adding",
            "allow",
            "enable",
            "enhance",
            "feature",
            "implement",
            "improve",
            "support",
        )
    ):
        return "features"
    if paths and all(
        path.startswith(("tests/", ".github/"))
        or path in {"pyproject.toml", ".gitignore"}
        for path in paths
    ):
        return "internal"
    if any(pattern in text for pattern in LOW_VALUE_PATTERNS):
        return "internal"
    if any(path.startswith((".github/", "tests/")) for path in paths):
        return "maintenance"
    return "uncategorized"


def release_note_value(category: str, title: str, paths: list[str]) -> bool:
    """Return False for changes that are probably too internal for release notes."""
    title_lower = title.casefold()
    if category == "internal":
        return False
    if any(pattern in title_lower for pattern in LOW_VALUE_PATTERNS):
        return False
    if paths and all(path.startswith(("tests/", ".github/")) for path in paths):
        return False
    return True


def issue_summaries(
    issues_by_number: dict[int, IssueRecord],
    numbers: list[int],
) -> list[dict[str, Any]]:
    """Return compact issue metadata for linked numbers."""
    summaries = []
    for number in numbers:
        issue = issues_by_number.get(number)
        if issue is None:
            summaries.append({"number": number})
            continue
        summaries.append(
            {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "labels": issue.labels,
                "is_pull_request": issue.is_pull_request,
            }
        )
    return summaries


def summarize_pull_request(
    pull_request: PullRequestRecord,
    issues_by_number: dict[int, IssueRecord],
) -> dict[str, Any]:
    """Return a compact PR summary record."""
    category = classify_change(
        pull_request.title,
        pull_request.body,
        pull_request.labels,
        changed_paths(pull_request.changed_files),
    )
    return {
        "id": f"pr:{pull_request.number}",
        "kind": "pull_request",
        "category": category,
        "title": pull_request.title,
        "body": truncate_text(pull_request.body),
        "author": pull_request.user_login,
        "url": pull_request.html_url,
        "merged_at": pull_request.merged_at,
        "merge_commit_sha": pull_request.merge_commit_sha,
        "labels": pull_request.labels,
        "changed_file_count": pull_request.changed_file_count,
        "additions": pull_request.additions,
        "deletions": pull_request.deletions,
        "linked_issues": issue_summaries(
            issues_by_number,
            pull_request.referenced_numbers,
        ),
        "release_note_candidate": True,
    }


def summarize_direct_commit(
    commit: CommitRecord,
    issues_by_number: dict[int, IssueRecord],
) -> dict[str, Any]:
    """Return a compact direct-commit summary record."""
    paths = changed_paths(commit.changed_files)
    category = classify_change(commit.title, commit.body, [], paths)
    return {
        "id": f"commit:{commit.short_sha}",
        "kind": "direct_commit",
        "category": category,
        "title": commit.title,
        "body": truncate_text(commit.body),
        "author": {
            "name": commit.author.name,
            "email": commit.author.email,
        },
        "sha": commit.sha,
        "date": commit.author_date,
        "changed_paths": paths[:20],
        "changed_file_count": len(paths),
        "additions": commit.additions,
        "deletions": commit.deletions,
        "linked_issues": issue_summaries(
            issues_by_number,
            commit.referenced_issues,
        ),
        "release_note_candidate": release_note_value(category, commit.title, paths),
    }


def contributor_summary(data: ReleaseData) -> dict[str, Any]:
    """Build all/first-time contributor summaries."""
    previous = previous_git_contributors(data.release.from_ref)
    contributors: dict[str, dict[str, Any]] = {}

    for commit in data.commits:
        key = person_key(commit.author.name, commit.author.email)
        contributor = contributors.setdefault(
            key,
            {
                "name": commit.author.name,
                "email": commit.author.email,
                "github_login": None,
                "commits": 0,
                "pull_requests": 0,
                "first_time": key not in previous,
            },
        )
        contributor["commits"] += 1

    pull_request_authors: dict[str, dict[str, Any]] = {}
    for pull_request in data.pull_requests:
        if pull_request.user_login is None:
            continue
        key = pull_request.user_login.casefold()
        pull_request_author = pull_request_authors.setdefault(
            key,
            {
                "github_login": pull_request.user_login,
                "pull_requests": 0,
            },
        )
        pull_request_author["pull_requests"] += 1

    all_contributors = sorted(
        contributors.values(),
        key=lambda contributor: (str(contributor["name"]).casefold()),
    )
    return {
        "all": all_contributors,
        "first_time": [
            contributor for contributor in all_contributors if contributor["first_time"]
        ],
        "pull_request_authors": sorted(
            pull_request_authors.values(),
            key=lambda contributor: contributor["github_login"].casefold(),
        ),
    }


def build_release_summary(data: ReleaseData) -> dict[str, Any]:
    """Build a condensed LLM-oriented release summary."""
    issues_by_number = {issue.number: issue for issue in data.issues}
    pr_merge_shas = {
        pull_request.merge_commit_sha
        for pull_request in data.pull_requests
        if pull_request.merge_commit_sha
    }

    changes_by_category: dict[str, list[dict[str, Any]]] = {
        category: [] for category in SUMMARY_CATEGORIES
    }
    for pull_request in data.pull_requests:
        summary = summarize_pull_request(pull_request, issues_by_number)
        changes_by_category[summary["category"]].append(summary)

    direct_commits = [
        commit
        for commit in data.commits
        if not commit.is_merge and commit.sha not in pr_merge_shas
    ]
    for commit in direct_commits:
        summary = summarize_direct_commit(commit, issues_by_number)
        if summary["release_note_candidate"]:
            changes_by_category[summary["category"]].append(summary)

    closed_issues = [
        {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "labels": issue.labels,
            "closed_at": issue.closed_at,
            "referenced_by": issue.referenced_by,
            "linked_commits": [sha[:8] for sha in issue.linked_commits],
        }
        for issue in data.issues
        if not issue.is_pull_request and "closed_in_range" in issue.source
    ]

    return {
        "release": asdict(data.release),
        "counts": {
            "commits": len(data.commits),
            "pull_requests": len(data.pull_requests),
            "issues": len(data.issues),
            "closed_issues": len(closed_issues),
            "direct_commits_considered": len(direct_commits),
            "release_note_candidates": sum(
                len(changes) for changes in changes_by_category.values()
            ),
        },
        "changes_by_category": changes_by_category,
        "closed_issues": closed_issues,
        "contributors": contributor_summary(data),
        "llm_instructions": [
            "Use this summary as source material, not as a changelog to copy verbatim.",
            "Prefer user-visible changes over internal maintenance.",
            "Deduplicate related PRs, commits, and issues into concise release-note bullets.",
            "Mention first-time contributors by GitHub login when available.",
        ],
    }


def detect_areas(title: str, paths: list[str]) -> list[str]:
    """Detect broad API areas touched by a topic."""
    title_lower = title.casefold()
    areas = set()
    checks = (
        ("topology", ("src/build123d/topology/", "topology")),
        (
            "geometry",
            ("src/build123d/geometry.py", "vector", "plane", "axis", "location"),
        ),
        (
            "objects",
            ("src/build123d/objects", "circle", "arc", "line", "box", "cylinder"),
        ),
        (
            "builders",
            (
                "src/build123d/build_",
                "builder",
                "buildpart",
                "buildsketch",
                "buildline",
            ),
        ),
        ("selectors", ("selector", "filter_by", "sort_by", "group_by")),
        ("import_export", ("import", "export", "stl", "step", "3mf", "dxf", "gltf")),
        ("text_fonts", ("text", "font", "singleline")),
        ("docs_examples", ("docs/", "examples/", "tutorial", "readme", "example")),
        ("ci_packaging", (".github/", "pyproject.toml", "pytest", "mypy", "action")),
    )
    haystack = "\n".join([title_lower, *(path.casefold() for path in paths)])
    for area, needles in checks:
        if any(needle in haystack for needle in needles):
            areas.add(area)
    return sorted(areas) or ["general"]


def source_sort_key(source_id: str) -> tuple[int, str]:
    """Sort PRs before commits in topic sources."""
    return (0 if source_id.startswith("pr:") else 1, source_id)


def topic_key_for_change(change: dict[str, Any]) -> str:
    """Group related changes by linked issue first, then source."""
    linked_numbers = [
        issue["number"]
        for issue in change.get("linked_issues", [])
        if not issue.get("is_pull_request", False) and "number" in issue
    ]
    if linked_numbers:
        return f"issue:{linked_numbers[0]}"
    if change["kind"] == "pull_request":
        return change["id"]
    return change["id"]


def issue_title_for_topic(
    key: str,
    issues_by_number: dict[int, dict[str, Any]],
) -> str | None:
    """Return issue title for issue-keyed topics."""
    if not key.startswith("issue:"):
        return None
    number = int(key.split(":", maxsplit=1)[1])
    issue = issues_by_number.get(number)
    return issue["title"] if issue else None


def merge_topic_change(topic: dict[str, Any], change: dict[str, Any]) -> None:
    """Merge one change candidate into a topic."""
    topic["source_ids"].append(change["id"])
    topic["source_ids"].sort(key=source_sort_key)
    topic["titles"].append(change["title"])
    topic["authors"].update(
        [change["author"]]
        if isinstance(change.get("author"), str) and change.get("author")
        else []
    )
    topic["additions"] += change.get("additions", 0)
    topic["deletions"] += change.get("deletions", 0)
    topic["changed_file_count"] += change.get("changed_file_count", 0)
    topic["linked_issues"].update(
        issue["number"]
        for issue in change.get("linked_issues", [])
        if "number" in issue
    )
    paths = change.get("changed_paths", [])
    topic["areas"].update(detect_areas(change["title"], paths))
    if change.get("body") and len(topic["body_hints"]) < 3:
        topic["body_hints"].append(change["body"])


def topic_score(topic: dict[str, Any]) -> tuple[int, int, int, int]:
    """Rank topics within a category."""
    source_count = len(topic["source_ids"])
    issue_count = len(topic["linked_issues"])
    size = topic["changed_file_count"] + topic["additions"] // 50
    has_pr = any(source_id.startswith("pr:") for source_id in topic["source_ids"])
    return (1 if has_pr else 0, issue_count, source_count, size)


def build_topic_groups(
    summary: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Collapse candidate changes into issue/PR/direct-commit topics."""
    closed_issues_by_number = {
        issue["number"]: issue for issue in summary["closed_issues"]
    }
    grouped: dict[str, dict[str, dict[str, Any]]] = {
        category: {} for category in SUMMARY_CATEGORIES
    }

    for category, changes in summary["changes_by_category"].items():
        for change in changes:
            if category == "internal":
                continue
            key = topic_key_for_change(change)
            title = (
                issue_title_for_topic(key, closed_issues_by_number) or change["title"]
            )
            topic = grouped[category].setdefault(
                key,
                {
                    "topic_id": key,
                    "category": category,
                    "title_hint": title,
                    "titles": [],
                    "body_hints": [],
                    "source_ids": [],
                    "linked_issues": set(),
                    "areas": set(),
                    "authors": set(),
                    "additions": 0,
                    "deletions": 0,
                    "changed_file_count": 0,
                },
            )
            merge_topic_change(topic, change)

    selected: dict[str, list[dict[str, Any]]] = {}
    omitted_counts: dict[str, int] = {}
    for category, topics_by_key in grouped.items():
        topics = list(topics_by_key.values())
        topics.sort(key=topic_score, reverse=True)
        limit = TOPIC_LIMITS.get(category, 10)
        selected_topics = topics[:limit]
        omitted_counts[category] = max(0, len(topics) - len(selected_topics))
        selected[category] = [
            {
                "topic_id": topic["topic_id"],
                "category": topic["category"],
                "title_hint": topic["title_hint"],
                "source_ids": topic["source_ids"],
                "linked_issues": sorted(topic["linked_issues"]),
                "areas": sorted(topic["areas"]),
                "authors": sorted(topic["authors"]),
                "related_titles": topic["titles"][:8],
                "body_hints": topic["body_hints"],
                "changed_file_count": topic["changed_file_count"],
                "additions": topic["additions"],
                "deletions": topic["deletions"],
            }
            for topic in selected_topics
        ]

    return selected, omitted_counts


def compatibility_candidates(summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract review candidates for compatibility notes."""
    candidates: dict[str, dict[str, Any]] = {}
    for category, changes in summary["changes_by_category"].items():
        for change in changes:
            text = "\n".join(str(change.get(key, "")) for key in ("title", "body"))
            reasons = [
                reason
                for reason, pattern in COMPATIBILITY_PATTERNS
                if pattern.search(text)
            ]
            if not reasons:
                continue
            candidates[change["id"]] = {
                "id": change["id"],
                "category": category,
                "title": change["title"],
                "reasons": sorted(reasons),
                "kind": change["kind"],
                "source_ids": [change["id"]],
                "linked_issues": [
                    issue
                    for issue in change.get("linked_issues", [])
                    if not issue.get("is_pull_request", False)
                ],
                "changed_paths": change.get("changed_paths", [])[:12],
                "body_hint": truncate_text(change.get("body", ""), 700),
                "review_note": (
                    "Review before describing as breaking; this is a "
                    "compatibility signal, not a confirmed breaking change."
                ),
            }

    return sorted(
        candidates.values(),
        key=lambda candidate: (
            candidate["reasons"][0],
            source_sort_key(candidate["id"]),
        ),
    )


def build_llm_input(summary: dict[str, Any]) -> dict[str, Any]:
    """Build the tighter LLM input from the broader release summary."""
    topics_by_category, omitted_counts = build_topic_groups(summary)
    compatibility = compatibility_candidates(summary)
    topic_count = sum(len(topics) for topics in topics_by_category.values())
    return {
        "release": summary["release"],
        "counts": {
            **summary["counts"],
            "llm_topics": topic_count,
            "omitted_topics": sum(omitted_counts.values()),
            "compatibility_candidates": len(compatibility),
        },
        "topics_by_category": topics_by_category,
        "compatibility_candidates": compatibility,
        "omitted_topic_counts": omitted_counts,
        "contributors": {
            "first_time": summary["contributors"]["first_time"],
            "pull_request_authors": summary["contributors"]["pull_request_authors"],
        },
        "llm_instructions": [
            "Write concise release notes for users of build123d.",
            "Do not create one bullet per topic; merge related topics into readable bullets.",
            (
                "Prefer user-visible APIs, behavior changes, import/export "
                "improvements, and important bug fixes."
            ),
            "Keep maintenance/internal details brief unless they affect users directly.",
            (
                "Use compatibility_candidates to draft a Compatibility Notes "
                "section, but do not call an item breaking unless the evidence "
                "clearly supports it."
            ),
            (
                "Use source_ids and linked_issues only for traceability; do "
                "not include all of them in prose."
            ),
            (
                "Include a first-time contributors section using the "
                "contributor names/logins provided."
            ),
        ],
    }


def github_repo_url(owner: str, repo: str) -> str:
    """Return the GitHub repository URL."""
    return f"https://github.com/{owner}/{repo}"


def commit_url(owner: str, repo: str, sha: str) -> str:
    """Return the GitHub commit URL."""
    return f"{github_repo_url(owner, repo)}/commit/{sha}"


def compare_url(owner: str, repo: str, from_ref: str, to_ref: str) -> str:
    """Return the GitHub compare URL for the release."""
    return f"{github_repo_url(owner, repo)}/compare/{from_ref}...{to_ref}"


def pr_by_merge_sha(data: ReleaseData) -> dict[str, PullRequestRecord]:
    """Map merge commit SHAs to pull requests."""
    return {
        pull_request.merge_commit_sha: pull_request
        for pull_request in data.pull_requests
        if pull_request.merge_commit_sha
    }


def commit_by_short_sha(data: ReleaseData) -> dict[str, CommitRecord]:
    """Map short commit SHAs to commit records."""
    return {commit.short_sha: commit for commit in data.commits}


def github_style_source(
    source_id: str,
    owner: str,
    repo: str,
    prs_by_number: dict[int, PullRequestRecord],
    commits_by_short_sha: dict[str, CommitRecord],
) -> dict[str, Any]:
    """Return link/author details for a PR or commit source id."""
    if source_id.startswith("pr:"):
        number = int(source_id.split(":", maxsplit=1)[1])
        pull_request = prs_by_number[number]
        return {
            "id": source_id,
            "kind": "pull_request",
            "title": pull_request.title,
            "author": pull_request.user_login,
            "reference": f"#{pull_request.number}",
            "url": pull_request.html_url,
        }

    short_sha = source_id.split(":", maxsplit=1)[1]
    commit = commits_by_short_sha[short_sha]
    return {
        "id": source_id,
        "kind": "commit",
        "title": commit.title,
        "author": commit.author.name,
        "reference": commit.short_sha,
        "url": commit_url(owner, repo, commit.sha),
    }


def selected_other_change(
    change: dict[str, Any],
    owner: str,
    repo: str,
    prs_by_number: dict[int, PullRequestRecord],
    commits_by_short_sha: dict[str, CommitRecord],
) -> dict[str, Any]:
    """Build a detailed GitHub-release-style selected change record."""
    source = github_style_source(
        change["id"],
        owner,
        repo,
        prs_by_number,
        commits_by_short_sha,
    )
    return {
        "title": change["title"],
        "category": change["category"],
        "source": source,
        "linked_issues": change.get("linked_issues", []),
        "suggested_bullet_style": (
            "- {title} by @{author} in {reference}"
            if source["kind"] == "pull_request"
            else "- {title} by {author} in {reference}"
        ),
    }


def github_style_compatibility_candidate(
    candidate: dict[str, Any],
    owner: str,
    repo: str,
    prs_by_number: dict[int, PullRequestRecord],
    commits_by_short_sha: dict[str, CommitRecord],
) -> dict[str, Any]:
    """Add GitHub-style source links to a compatibility candidate."""
    return {
        **candidate,
        "sources": [
            github_style_source(
                source_id,
                owner,
                repo,
                prs_by_number,
                commits_by_short_sha,
            )
            for source_id in candidate["source_ids"]
        ],
    }


def github_style_new_contributors(
    summary: dict[str, Any],
    owner: str,
    repo: str,
    commits_by_short_sha: dict[str, CommitRecord],
) -> list[dict[str, Any]]:
    """Build first-time contributor records with available source links."""
    contributors = []
    for contributor in summary["contributors"]["first_time"]:
        first_commit = None
        for short_sha, commit in commits_by_short_sha.items():
            if (
                commit.author.name == contributor["name"]
                and commit.author.email == contributor["email"]
            ):
                first_commit = commit
                break

        source = None
        if first_commit is not None:
            source = {
                "kind": "commit",
                "reference": first_commit.short_sha,
                "url": commit_url(owner, repo, first_commit.sha),
                "title": first_commit.title,
            }

        contributors.append(
            {
                "name": contributor["name"],
                "github_login": contributor.get("github_login"),
                "source": source,
            }
        )
    return contributors


def build_github_notes_input(
    data: ReleaseData,
    summary: dict[str, Any],
    owner: str,
    repo: str,
) -> dict[str, Any]:
    """Build a single LLM input for GitHub-style release notes."""
    llm_input = build_llm_input(summary)
    prs_by_number = {
        pull_request.number: pull_request for pull_request in data.pull_requests
    }
    commits_by_short_sha = commit_by_short_sha(data)
    selected_changes = []
    for category, changes in summary["changes_by_category"].items():
        if category == "internal":
            continue
        for change in changes:
            if not change.get("release_note_candidate", True):
                continue
            selected_changes.append(
                selected_other_change(
                    change,
                    owner,
                    repo,
                    prs_by_number,
                    commits_by_short_sha,
                )
            )

    selected_changes.sort(
        key=lambda change: (
            change["category"],
            source_sort_key(change["source"]["id"]),
        )
    )

    return {
        "release": {
            **summary["release"],
            "repository_url": github_repo_url(owner, repo),
            "full_changelog_url": compare_url(
                owner,
                repo,
                data.release.from_ref,
                data.release.to_ref,
            ),
        },
        "output_template": {
            "title": "build123d {version}",
            "sections": [
                {
                    "heading": "Breaking Changes",
                    "optional": True,
                    "instructions": (
                        "Only include confirmed backwards-incompatible changes. "
                        "Omit this section if none are confirmed."
                    ),
                },
                {
                    "heading": "Compatibility Notes",
                    "optional": True,
                    "instructions": (
                        "Include deprecations, moved APIs, changed defaults, "
                        "and behavior changes users should review."
                    ),
                },
                {
                    "heading": "Notable Changes",
                    "instructions": (
                        "Use 8-15 bullets. Prefer grouped, user-visible "
                        "changes over individual commits."
                    ),
                },
                {
                    "heading": "Selected Other Changes",
                    "instructions": (
                        "Use detailed bullets with author and PR/commit links. "
                        "Do not include every selected change."
                    ),
                },
                {
                    "heading": "New Contributors",
                    "optional": True,
                    "instructions": (
                        "Thank first-time contributors. Use source links when "
                        "available."
                    ),
                },
                {
                    "heading": "Full Changelog",
                    "instructions": "Include the full changelog compare link.",
                },
            ],
        },
        "style_guide": [
            "Match the existing build123d GitHub release-note style.",
            "Use concise Markdown bullets.",
            "Prefer 'by @user in #123' for pull requests.",
            "Use direct commit links only when no PR exists.",
            "Do not list every commit.",
            "Keep compatibility notes separate from confirmed breaking changes.",
        ],
        "example_bullets": [
            "Added a new `Face.wrap` method by @gumyr.",
            "@jwagenet added four new 1D tangent objects in #947.",
            (
                "Fix `revolve` direction and size with negative "
                "`revolution_arc` by @jwagenet in #964."
            ),
            "Deprecating `Color.to_tuple` by @gumyr in 83cea39.",
        ],
        "notable_topics": llm_input["topics_by_category"],
        "compatibility_candidates": [
            github_style_compatibility_candidate(
                candidate,
                owner,
                repo,
                prs_by_number,
                commits_by_short_sha,
            )
            for candidate in llm_input["compatibility_candidates"]
        ],
        "selected_other_changes": selected_changes[:160],
        "new_contributors": github_style_new_contributors(
            summary,
            owner,
            repo,
            commits_by_short_sha,
        ),
        "contributors": llm_input["contributors"],
        "counts": {
            **llm_input["counts"],
            "selected_other_changes": min(len(selected_changes), 160),
            "selected_other_changes_available": len(selected_changes),
        },
        "llm_instructions": [
            "Generate Markdown suitable for a GitHub release body.",
            "Follow output_template section order.",
            "Use notable_topics for the Notable Changes section.",
            (
                "Use selected_other_changes for detailed linked bullets, but "
                "choose the most useful subset."
            ),
            (
                "Use compatibility_candidates for Compatibility Notes; do not "
                "claim Breaking Changes unless the item is clearly breaking."
            ),
            "Include new_contributors and the full_changelog_url.",
        ],
    }


def github_token() -> str:
    """Return a GitHub token from the environment."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    raise RuntimeError(
        "No GitHub token found. Set GITHUB_TOKEN or use --no-auth for public-only probes."
    )


def cache_path_for(cache_dir: Path, path: str) -> Path:
    """Return a cache file path for a GitHub API path."""
    digest = sha256(path.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.json"


def github_get_json(path: str, token: str | None, cache_dir: Path | None) -> Any:
    """GET a GitHub API path and decode JSON."""
    if cache_dir is not None:
        cached_response = cache_path_for(cache_dir, path)
        if cached_response.exists():
            return json.loads(cached_response.read_text())

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "build123d-release-notes-tool",
    }
    if token is not None:
        headers["Authorization"] = f"token {token}"

    request = Request(
        f"{GITHUB_API}{path}",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed: HTTP {err.code} {err.reason}: {detail}"
        ) from err
    except URLError as err:
        raise RuntimeError(f"GitHub API request failed: {err.reason}") from err

    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path_for(cache_dir, path).write_text(f"{json.dumps(payload)}\n")
    return payload


def github_get_paginated(
    path: str,
    token: str | None,
    cache_dir: Path | None,
) -> list[Any]:
    """Fetch all pages for a GitHub API endpoint that returns a list."""
    items: list[Any] = []
    page = 1
    while True:
        separator = "&" if "?" in path else "?"
        payload = github_get_json(
            f"{path}{separator}per_page=100&page={page}",
            token,
            cache_dir,
        )
        if isinstance(payload, dict) and "items" in payload:
            page_items = payload["items"]
        else:
            page_items = payload
        if not isinstance(page_items, list):
            raise RuntimeError(f"Unexpected paginated GitHub payload at {path}")

        items.extend(page_items)
        if len(page_items) < 100:
            break
        page += 1
    return items


def fetch_latest_commit(
    owner: str,
    repo: str,
    token: str | None,
    cache_dir: Path | None,
) -> CommitSample:
    """Fetch one commit to prove GitHub API access works."""
    payload = github_get_json(
        f"/repos/{owner}/{repo}/commits?per_page=1",
        token,
        cache_dir,
    )
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("GitHub returned no commits")

    commit = payload[0]
    commit_data = commit.get("commit", {})
    author_data = commit_data.get("author") or {}
    message = commit_data.get("message") or ""
    github_author = commit.get("author") or {}

    return CommitSample(
        sha=commit.get("sha", ""),
        html_url=commit.get("html_url", ""),
        author_name=author_data.get("name"),
        author_login=github_author.get("login"),
        date=author_data.get("date"),
        message_headline=message.splitlines()[0] if message else "",
    )


def github_date(date_text: str) -> str:
    """Return YYYY-MM-DD for GitHub search qualifiers."""
    return datetime.fromisoformat(date_text).date().isoformat()


def parse_github_datetime(date_text: str) -> datetime:
    """Parse a GitHub UTC timestamp."""
    return datetime.fromisoformat(date_text.replace("Z", "+00:00"))


def fetch_pull_request_files(
    owner: str,
    repo: str,
    number: int,
    token: str | None,
    cache_dir: Path | None,
) -> list[ChangedFile]:
    """Fetch changed files for a pull request."""
    files = github_get_paginated(
        f"/repos/{owner}/{repo}/pulls/{number}/files",
        token,
        cache_dir,
    )
    return [
        ChangedFile(
            path=file_data.get("filename", ""),
            additions=file_data.get("additions"),
            deletions=file_data.get("deletions"),
        )
        for file_data in files
    ]


def fetch_pull_request(
    owner: str,
    repo: str,
    number: int,
    token: str | None,
    include_files: bool,
    cache_dir: Path | None,
) -> PullRequestRecord:
    """Fetch a pull request and normalize release-note metadata."""
    pr = github_get_json(f"/repos/{owner}/{repo}/pulls/{number}", token, cache_dir)
    files = (
        fetch_pull_request_files(owner, repo, number, token, cache_dir)
        if include_files
        else []
    )
    body = pr.get("body") or ""
    title = pr.get("title") or ""
    user = pr.get("user") or {}
    return PullRequestRecord(
        number=pr.get("number"),
        title=title,
        body=body,
        state=pr.get("state", ""),
        user_login=user.get("login"),
        html_url=pr.get("html_url", ""),
        created_at=pr.get("created_at", ""),
        updated_at=pr.get("updated_at", ""),
        merged_at=pr.get("merged_at", ""),
        merge_commit_sha=pr.get("merge_commit_sha"),
        changed_file_count=pr.get("changed_files", 0),
        labels=[label.get("name", "") for label in pr.get("labels", [])],
        changed_files=files,
        additions=pr.get("additions", 0),
        deletions=pr.get("deletions", 0),
        referenced_numbers=extract_number_refs(f"{title}\n{body}"),
    )


def fetch_issue_comments(
    owner: str,
    repo: str,
    number: int,
    token: str | None,
    cache_dir: Path | None,
) -> list[str]:
    """Fetch issue comment bodies."""
    comments = github_get_paginated(
        f"/repos/{owner}/{repo}/issues/{number}/comments",
        token,
        cache_dir,
    )
    return [comment.get("body") or "" for comment in comments]


def fetch_issue(
    owner: str,
    repo: str,
    number: int,
    token: str | None,
    source: set[str],
    referenced_by: set[str],
    commits_by_sha: dict[str, CommitRecord],
    include_comments: bool,
    cache_dir: Path | None,
) -> IssueRecord:
    """Fetch one GitHub issue or PR-as-issue and normalize metadata."""
    issue = github_get_json(f"/repos/{owner}/{repo}/issues/{number}", token, cache_dir)
    body = issue.get("body") or ""
    comments = (
        fetch_issue_comments(owner, repo, number, token, cache_dir)
        if include_comments
        else []
    )
    linked_commits = extract_commit_links(
        "\n".join([body, *comments]),
        commits_by_sha,
    )
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


def collect_closed_issue_numbers(
    owner: str,
    repo: str,
    from_date: str,
    to_date: str,
    token: str | None,
    cache_dir: Path | None,
) -> set[int]:
    """Collect issue numbers closed in the exact release date range."""
    query = " ".join(
        [
            f"repo:{owner}/{repo}",
            "is:issue",
            f"closed:{github_date(from_date)}..{github_date(to_date)}",
        ]
    )
    search_path = (
        f"/search/issues?{urlencode({'q': query, 'sort': 'updated', 'order': 'asc'})}"
    )
    search_items = github_get_paginated(search_path, token, cache_dir)
    from_datetime = datetime.fromisoformat(from_date)
    to_datetime = datetime.fromisoformat(to_date)
    return {
        item["number"]
        for item in search_items
        if (
            item.get("closed_at")
            and from_datetime < parse_github_datetime(item["closed_at"]) <= to_datetime
        )
    }


def collect_issues(
    owner: str,
    repo: str,
    release: ReleaseRange,
    commits: list[CommitRecord],
    pull_requests: list[PullRequestRecord],
    token: str | None,
    include_comments: bool = True,
    cache_dir: Path | None = None,
) -> list[IssueRecord]:
    """Collect referenced and closed issues for the release."""
    commits_by_sha = {commit.sha: commit for commit in commits}
    referenced_numbers = referenced_numbers_from_release_inputs(commits, pull_requests)
    issue_sources: dict[int, set[str]] = {
        number: {"referenced"} for number in referenced_numbers
    }
    issue_references: dict[int, set[str]] = {
        number: set(references) for number, references in referenced_numbers.items()
    }

    closed_numbers = collect_closed_issue_numbers(
        owner,
        repo,
        release.from_date,
        release.to_date,
        token,
        cache_dir,
    )
    for number in closed_numbers:
        issue_sources.setdefault(number, set()).add("closed_in_range")
        issue_references.setdefault(number, set())

    print(
        f"fetching {len(issue_sources)} issues/PR-number references "
        f"({len(closed_numbers)} closed issues)",
        file=sys.stderr,
    )

    issues: list[IssueRecord] = []
    for number in sorted(issue_sources):
        try:
            issues.append(
                fetch_issue(
                    owner,
                    repo,
                    number,
                    token,
                    issue_sources[number],
                    issue_references[number],
                    commits_by_sha,
                    include_comments,
                    cache_dir,
                )
            )
        except RuntimeError as err:
            print(f"warning: could not fetch issue #{number}: {err}", file=sys.stderr)

    return issues


def collect_merged_pull_requests(
    owner: str,
    repo: str,
    from_date: str,
    to_date: str,
    token: str | None,
    include_files: bool = False,
    cache_dir: Path | None = None,
) -> list[PullRequestRecord]:
    """Collect merged pull requests in the release date range."""
    query = " ".join(
        [
            f"repo:{owner}/{repo}",
            "is:pr",
            "is:merged",
            f"merged:{github_date(from_date)}..{github_date(to_date)}",
        ]
    )
    search_path = (
        f"/search/issues?{urlencode({'q': query, 'sort': 'created', 'order': 'asc'})}"
    )
    search_items = github_get_paginated(search_path, token, cache_dir)
    from_datetime = datetime.fromisoformat(from_date)
    to_datetime = datetime.fromisoformat(to_date)
    search_items = [
        item
        for item in search_items
        if (
            item.get("pull_request", {}).get("merged_at")
            and from_datetime
            < parse_github_datetime(item["pull_request"]["merged_at"])
            <= to_datetime
        )
    ]
    print(f"fetching {len(search_items)} merged PRs", file=sys.stderr)

    pull_requests = [
        fetch_pull_request(owner, repo, item["number"], token, include_files, cache_dir)
        for item in search_items
    ]
    pull_requests.sort(key=lambda pr: pr.merged_at)
    return pull_requests


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect GitHub data for build123d release notes."
    )
    parser.add_argument("--owner", default=DEFAULT_OWNER)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument(
        "--from-tag",
        dest="from_ref",
        help="Collect release data from this tag/ref, e.g. v0.10.0.",
    )
    parser.add_argument(
        "--from-ref",
        dest="from_ref",
        help="Collect release data from this tag/ref, e.g. v0.10.0.",
    )
    parser.add_argument(
        "--to-ref",
        default="HEAD",
        help="Collect release data up to this tag/ref. Defaults to HEAD.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write release data JSON to this path instead of stdout.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write condensed release-summary JSON to this path.",
    )
    parser.add_argument(
        "--llm-input-output",
        type=Path,
        help="Write tightly grouped LLM input JSON to this path.",
    )
    parser.add_argument(
        "--github-notes-input-output",
        type=Path,
        help="Write GitHub-release-style LLM input JSON to this path.",
    )
    parser.add_argument(
        "--include-pr-files",
        action="store_true",
        help="Fetch per-file PR details. Slower; commit file details are always collected.",
    )
    parser.add_argument(
        "--skip-issue-comments",
        action="store_true",
        help="Do not fetch issue comments while collecting linked/closed issues.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"GitHub API response cache directory. Defaults to {DEFAULT_CACHE_DIR}.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable the GitHub API response cache.",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Do not send a GitHub token; useful for separating connectivity from auth.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entry point."""
    args = parse_args()
    cache_dir = None if args.no_cache else args.cache_dir
    if args.from_ref:
        try:
            token = None if args.no_auth else github_token()
            release_data = collect_release_data(
                args.owner,
                args.repo,
                args.from_ref,
                args.to_ref,
                token,
                args.include_pr_files,
                not args.skip_issue_comments,
                cache_dir,
            )
        except (RuntimeError, subprocess.CalledProcessError) as err:
            print(f"error: {err}", file=sys.stderr)
            return 1

        raw_output = json.dumps(asdict(release_data), indent=2)
        summary = build_release_summary(release_data)
        summary_output = json.dumps(summary, indent=2)
        llm_input = build_llm_input(summary)
        llm_input_output = json.dumps(llm_input, indent=2)
        github_notes_input = build_github_notes_input(
            release_data,
            summary,
            args.owner,
            args.repo,
        )
        github_notes_output = json.dumps(github_notes_input, indent=2)
        if args.summary_output:
            args.summary_output.write_text(f"{summary_output}\n")
            print(
                f"wrote summary with "
                f"{summary['counts']['release_note_candidates']} candidates to "
                f"{args.summary_output}",
                file=sys.stderr,
            )
        if args.llm_input_output:
            args.llm_input_output.write_text(f"{llm_input_output}\n")
            print(
                f"wrote LLM input with "
                f"{llm_input['counts']['llm_topics']} topics to "
                f"{args.llm_input_output}",
                file=sys.stderr,
            )
        if args.github_notes_input_output:
            args.github_notes_input_output.write_text(f"{github_notes_output}\n")
            print(
                f"wrote GitHub notes input with "
                f"{github_notes_input['counts']['selected_other_changes']} "
                f"selected changes to {args.github_notes_input_output}",
                file=sys.stderr,
            )
        if args.output:
            args.output.write_text(f"{raw_output}\n")
            print(
                f"wrote {len(release_data.commits)} commits and "
                f"{len(release_data.pull_requests)} PRs and "
                f"{len(release_data.issues)} issues to {args.output}",
                file=sys.stderr,
            )
        elif (
            not args.summary_output
            and not args.llm_input_output
            and not args.github_notes_input_output
        ):
            print(raw_output)
        return 0

    try:
        token = None if args.no_auth else github_token()
        commit = fetch_latest_commit(args.owner, args.repo, token, cache_dir)
    except RuntimeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(commit), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
