"""DSPy signatures for PR review and Issue triage tasks."""

from __future__ import annotations

import dspy


class ReviewPRSignature(dspy.Signature):
    """Analyse a code diff from a Pull Request and provide structured feedback.

    You are an expert code reviewer focusing on security, performance, and
    correctness.  Be specific, cite line numbers when possible, and
    prioritise actionable feedback.
    """

    diff: str = dspy.InputField(desc="Unified diff of the Pull Request changes")
    pr_title: str = dspy.InputField(desc="Title of the Pull Request")
    pr_body: str = dspy.InputField(desc="Description body of the Pull Request")

    security_risks: str = dspy.OutputField(
        desc=(
            "List of security risks found in the diff. "
            "Each item should describe the risk and suggest a fix. "
            "Return 'None found' if there are no security concerns."
        )
    )
    performance_issues: str = dspy.OutputField(
        desc=(
            "List of performance issues or inefficiencies. "
            "Include suggestions for improvement. "
            "Return 'None found' if there are no performance concerns."
        )
    )
    logic_flaws: str = dspy.OutputField(
        desc=(
            "List of logical errors, edge cases, or bugs. "
            "Explain why each is problematic and how to fix it. "
            "Return 'None found' if there are no logic issues."
        )
    )
    suggestions: str = dspy.OutputField(
        desc=(
            "General code quality suggestions: naming, structure, "
            "readability, best practices, and documentation improvements."
        )
    )
    overall_assessment: str = dspy.OutputField(
        desc=(
            "A concise overall assessment of the PR quality. "
            "Include a verdict: APPROVE, REQUEST_CHANGES, or COMMENT."
        )
    )


class TriageIssueSignature(dspy.Signature):
    """Analyse a GitHub Issue and suggest labels, priority, and a summary.

    You are an experienced open-source maintainer.  Classify the issue
    accurately and assign a priority score based on impact and urgency.
    """

    issue_title: str = dspy.InputField(desc="Title of the GitHub Issue")
    issue_body: str = dspy.InputField(desc="Full body text of the GitHub Issue")
    existing_labels: str = dspy.InputField(
        desc="Comma-separated list of labels already on the issue (may be empty)"
    )

    suggested_labels: str = dspy.OutputField(
        desc=(
            "Comma-separated list of suggested labels. "
            "Choose from: bug, feature, enhancement, documentation, "
            "question, good-first-issue, help-wanted, duplicate, "
            "invalid, wontfix, security, performance, breaking-change."
        )
    )
    priority_score: str = dspy.OutputField(
        desc=(
            "Priority score from 1 (lowest) to 5 (critical). "
            "Include a one-sentence justification."
        )
    )
    summary: str = dspy.OutputField(
        desc="A concise 1-2 sentence summary of what the issue is about."
    )
    suggested_assignee_expertise: str = dspy.OutputField(
        desc=(
            "What kind of expertise would be ideal for addressing this issue "
            "(e.g. 'frontend CSS', 'backend API', 'CI/CD', 'security')."
        )
    )
