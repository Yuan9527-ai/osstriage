"""GitHub API client with rate-limit handling and pagination support."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from github import Github, GithubException, RateLimitExceededException
from github.PullRequest import PullRequest as GHPullRequest
from github.Issue import Issue as GHIssue

from osstriage.core.exceptions import GitHubAPIError, RateLimitError
from osstriage.core.logging import get_logger

logger = get_logger("github_client")

# ---------------------------------------------------------------------------
# Data classes for clean return types
# ---------------------------------------------------------------------------

_GITHUB_URL_PATTERN = re.compile(
    r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/"
    r"(?P<type>pull|issues)/(?P<number>\d+)"
)


@dataclass(frozen=True, slots=True)
class PRData:
    """Structured representation of a Pull Request."""

    owner: str
    repo: str
    number: int
    title: str
    body: str
    diff: str
    author: str
    base_branch: str
    head_branch: str
    changed_files: int
    additions: int
    deletions: int


@dataclass(frozen=True, slots=True)
class IssueData:
    """Structured representation of a GitHub Issue."""

    owner: str
    repo: str
    number: int
    title: str
    body: str
    author: str
    labels: list[str]
    state: str
    comments_count: int


@dataclass(frozen=True, slots=True)
class ParsedURL:
    """Result of parsing a GitHub PR or Issue URL."""

    owner: str
    repo: str
    number: int
    type: str  # "pull" or "issues"


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


def parse_github_url(url: str) -> ParsedURL:
    """Parse a GitHub PR or Issue URL into its components.

    Args:
        url: Full GitHub URL (e.g. ``https://github.com/owner/repo/pull/42``).

    Returns:
        Parsed URL components.

    Raises:
        GitHubAPIError: If the URL format is invalid.
    """
    match = _GITHUB_URL_PATTERN.match(url.strip())
    if not match:
        raise GitHubAPIError(
            f"Invalid GitHub URL: '{url}'. "
            "Expected format: https://github.com/owner/repo/pull/123 "
            "or https://github.com/owner/repo/issues/123"
        )
    return ParsedURL(
        owner=match.group("owner"),
        repo=match.group("repo"),
        number=int(match.group("number")),
        type=match.group("type"),
    )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # seconds


class GitHubClient:
    """High-level wrapper around **PyGithub** with automatic rate-limit handling.

    Args:
        token: GitHub Personal Access Token.
    """

    def __init__(self, token: str) -> None:
        self._gh = Github(token, per_page=100)
        logger.info("GitHub client initialised")

    # -- Public API ---------------------------------------------------------

    def get_pr(self, owner: str, repo: str, pr_number: int) -> PRData:
        """Fetch a Pull Request including its unified diff.

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            pr_number: PR number.

        Returns:
            Structured :class:`PRData`.

        Raises:
            GitHubAPIError: On network or permission errors.
            RateLimitError: When the API rate limit is hit.
        """
        return self._retry(self._fetch_pr, owner, repo, pr_number)

    def get_issue(self, owner: str, repo: str, issue_number: int) -> IssueData:
        """Fetch a GitHub Issue.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue number.

        Returns:
            Structured :class:`IssueData`.
        """
        return self._retry(self._fetch_issue, owner, repo, issue_number)

    def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> None:
        """Post a review comment on a Pull Request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            body: Markdown comment body.
        """
        self._retry(self._post_comment, owner, repo, pr_number, body)
        logger.info("Review comment posted on %s/%s#%d", owner, repo, pr_number)

    def add_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
    ) -> None:
        """Add labels to an Issue or PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            issue_number: Issue or PR number.
            labels: List of label names to apply.
        """
        self._retry(self._add_labels, owner, repo, issue_number, labels)
        logger.info(
            "Labels %s added to %s/%s#%d", labels, owner, repo, issue_number
        )

    # -- Private helpers ----------------------------------------------------

    def _fetch_pr(self, owner: str, repo: str, pr_number: int) -> PRData:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        pr: GHPullRequest = repository.get_pull(pr_number)

        # Fetch the unified diff via the API
        diff = self._get_diff(pr)

        return PRData(
            owner=owner,
            repo=repo,
            number=pr.number,
            title=pr.title,
            body=pr.body or "",
            diff=diff,
            author=pr.user.login if pr.user else "unknown",
            base_branch=pr.base.ref,
            head_branch=pr.head.ref,
            changed_files=pr.changed_files,
            additions=pr.additions,
            deletions=pr.deletions,
        )

    @staticmethod
    def _get_diff(pr: GHPullRequest) -> str:
        """Retrieve the unified diff for a PR, handling large diffs."""
        files = pr.get_files()
        diff_parts: list[str] = []
        for f in files:
            header = f"--- a/{f.filename}\n+++ b/{f.filename}"
            patch = f.patch or "(binary or empty file)"
            diff_parts.append(f"{header}\n{patch}")
        return "\n\n".join(diff_parts)

    def _fetch_issue(
        self, owner: str, repo: str, issue_number: int
    ) -> IssueData:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        issue: GHIssue = repository.get_issue(issue_number)
        return IssueData(
            owner=owner,
            repo=repo,
            number=issue.number,
            title=issue.title,
            body=issue.body or "",
            author=issue.user.login if issue.user else "unknown",
            labels=[lbl.name for lbl in issue.labels],
            state=issue.state,
            comments_count=issue.comments,
        )

    def _post_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> None:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        pr = repository.get_pull(pr_number)
        pr.create_issue_comment(body)

    def _add_labels(
        self, owner: str, repo: str, issue_number: int, labels: list[str]
    ) -> None:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(issue_number)
        for label in labels:
            issue.add_to_labels(label)

    # -- Retry logic --------------------------------------------------------

    def _retry(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Call *func* with exponential backoff on rate-limit and transient errors."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException as exc:
                reset_time = self._gh.get_rate_limit().core.reset
                wait = max(
                    (reset_time.timestamp() - time.time()) + 1,
                    _BACKOFF_BASE ** (attempt + 1),
                )
                logger.warning(
                    "Rate limit hit (attempt %d/%d). Waiting %.0fs…",
                    attempt + 1,
                    _MAX_RETRIES,
                    wait,
                )
                if attempt == _MAX_RETRIES - 1:
                    raise RateLimitError(
                        reset_at=str(reset_time), cause=exc
                    ) from exc
                time.sleep(wait)
                last_exc = exc
            except GithubException as exc:
                logger.error(
                    "GitHub API error (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt == _MAX_RETRIES - 1:
                    raise GitHubAPIError(
                        f"GitHub API request failed after {_MAX_RETRIES} attempts: {exc}",
                        status_code=exc.status,
                        cause=exc,
                    ) from exc
                time.sleep(_BACKOFF_BASE ** (attempt + 1))
                last_exc = exc

        # Should never reach here, but satisfy the type checker
        raise GitHubAPIError(  # pragma: no cover
            "Unexpected retry exhaustion", cause=last_exc
        )
