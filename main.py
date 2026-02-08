"""
IssuePilot - GitHub Issue Triage API
Fetches issues from GitHub, classifies them using TF-IDF, and assigns priorities.
"""

import os
import json
import httpx
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

app = FastAPI(title="IssuePilot", description="GitHub Issue Triage System")

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DATA_FILE = "triaged_issues.json"

# Training data for classification
TRAINING_DATA = {
    "bug": [
        "error crash bug fail broken not working exception traceback",
        "fix issue problem broken defect failure regression",
        "error message stack trace debug crash freeze hang"
    ],
    "feature": [
        "add new feature enhancement request implement support",
        "would like feature request proposal improvement",
        "add support implement functionality enhancement capability"
    ],
    "docs": [
        "documentation readme update guide tutorial example",
        "documentation typo fix update clarify explain",
        "docs wiki help example usage guide instructions"
    ]
}

# Priority keywords
PRIORITY_KEYWORDS = {
    5: ["critical", "urgent", "security", "crash", "data loss", "blocking"],
    4: ["important", "high", "regression", "broken"],
    3: ["moderate", "normal", "enhancement"],
    2: ["minor", "low", "improvement"],
    1: ["trivial", "cosmetic", "typo"]
}


class Issue(BaseModel):
    """Issue model"""
    number: int
    title: str
    body: Optional[str]
    created_at: str
    state: str
    url: str


class TriagedIssue(BaseModel):
    """Triaged issue model"""
    number: int
    title: str
    body: Optional[str]
    created_at: str
    state: str
    url: str
    classification: str
    priority: int
    triaged_at: str


def load_triaged_issues() -> List[Dict]:
    """Load triaged issues from JSON file"""
    if not os.path.exists(DATA_FILE):
        return []
    
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []


def save_triaged_issues(issues: List[Dict]):
    """Save triaged issues to JSON file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(issues, f, indent=2)


def classify_issue(title: str, body: Optional[str]) -> str:
    """
    Classify issue using TF-IDF similarity
    
    Args:
        title: Issue title
        body: Issue body
        
    Returns:
        Classification: 'bug', 'feature', or 'docs'
    """
    # Combine title and body
    issue_text = f"{title} {body or ''}"
    
    # Prepare training documents
    documents = []
    labels = []
    for label, texts in TRAINING_DATA.items():
        for text in texts:
            documents.append(text)
            labels.append(label)
    
    # Add the issue to classify
    documents.append(issue_text)
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # Calculate similarity between issue and training data
    issue_vector = tfidf_matrix[-1]
    training_vectors = tfidf_matrix[:-1]
    
    similarities = cosine_similarity(issue_vector, training_vectors)[0]
    
    # Find best matching label
    best_idx = np.argmax(similarities)
    classification = labels[best_idx]
    
    return classification


def calculate_priority(title: str, body: Optional[str], created_at: str) -> int:
    """
    Calculate priority (1-5) based on keywords and age
    
    Args:
        title: Issue title
        body: Issue body
        created_at: Issue creation timestamp
        
    Returns:
        Priority: 1 (lowest) to 5 (highest)
    """
    text = f"{title} {body or ''}".lower()
    
    # Check for priority keywords
    keyword_priority = 3  # default
    for priority_level, keywords in sorted(PRIORITY_KEYWORDS.items(), reverse=True):
        if any(keyword in text for keyword in keywords):
            keyword_priority = priority_level
            break
    
    # Calculate age in days
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        age_days = (datetime.now(created.tzinfo) - created).days
        
        # Boost priority for old issues
        if age_days > 180:  # 6 months
            keyword_priority = min(5, keyword_priority + 1)
        elif age_days > 90:  # 3 months
            if keyword_priority < 5:
                keyword_priority = min(5, keyword_priority + 1)
    except Exception:
        pass
    
    return keyword_priority


async def fetch_github_issues(owner: str, repo: str, state: str = "open") -> List[Dict]:
    """
    Fetch issues from GitHub repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state (open, closed, all)
        
    Returns:
        List of issues
    """
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    params = {"state": state, "per_page": 100}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()
        issues = response.json()
    
    # Filter out pull requests (they appear in issues endpoint)
    issues = [issue for issue in issues if 'pull_request' not in issue]
    
    return issues


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IssuePilot - GitHub Issue Triage API",
        "endpoints": {
            "/sync": "Fetch and triage issues from GitHub",
            "/triage": "Manually triage a specific issue",
            "/list": "List all triaged issues"
        }
    }


@app.post("/sync")
async def sync_issues(
    owner: str = Query(..., description="Repository owner"),
    repo: str = Query(..., description="Repository name"),
    state: str = Query("open", description="Issue state: open, closed, or all")
):
    """
    Sync issues from GitHub and triage them
    
    Fetches issues from the specified repository and classifies them.
    """
    try:
        # Fetch issues from GitHub
        issues = await fetch_github_issues(owner, repo, state)
        
        if not issues:
            return {
                "status": "success",
                "message": "No issues found",
                "triaged_count": 0
            }
        
        # Load existing triaged issues
        triaged_issues = load_triaged_issues()
        existing_numbers = {issue["number"] for issue in triaged_issues}
        
        # Triage new issues
        new_triaged = []
        for issue in issues:
            # Skip if already triaged
            if issue["number"] in existing_numbers:
                continue
            
            # Classify and prioritize
            classification = classify_issue(issue["title"], issue.get("body"))
            priority = calculate_priority(
                issue["title"],
                issue.get("body"),
                issue["created_at"]
            )
            
            triaged = {
                "number": issue["number"],
                "title": issue["title"],
                "body": issue.get("body"),
                "created_at": issue["created_at"],
                "state": issue["state"],
                "url": issue["html_url"],
                "classification": classification,
                "priority": priority,
                "triaged_at": datetime.now().isoformat()
            }
            
            new_triaged.append(triaged)
            triaged_issues.append(triaged)
        
        # Save updated list
        save_triaged_issues(triaged_issues)
        
        return {
            "status": "success",
            "message": f"Synced and triaged {len(new_triaged)} new issues",
            "triaged_count": len(new_triaged),
            "total_issues": len(triaged_issues),
            "new_issues": new_triaged[:5]  # Return first 5 for preview
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"GitHub API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/triage")
async def triage_issue(
    title: str = Query(..., description="Issue title"),
    body: Optional[str] = Query(None, description="Issue body"),
    number: int = Query(..., description="Issue number"),
    created_at: Optional[str] = Query(None, description="Issue creation date (ISO format)")
):
    """
    Manually triage a specific issue
    
    Classifies and prioritizes an issue based on its title and body.
    """
    try:
        # Classify and prioritize
        classification = classify_issue(title, body)
        
        created = created_at or datetime.now().isoformat()
        priority = calculate_priority(title, body, created)
        
        result = {
            "number": number,
            "title": title,
            "body": body,
            "classification": classification,
            "priority": priority,
            "triaged_at": datetime.now().isoformat()
        }
        
        # Optionally save to storage
        triaged_issues = load_triaged_issues()
        
        # Update if exists, otherwise add
        existing_idx = None
        for idx, issue in enumerate(triaged_issues):
            if issue["number"] == number:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            triaged_issues[existing_idx].update(result)
        else:
            triaged_issues.append(result)
        
        save_triaged_issues(triaged_issues)
        
        return {
            "status": "success",
            "issue": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/list")
async def list_triaged_issues(
    classification: Optional[str] = Query(None, description="Filter by classification"),
    priority: Optional[int] = Query(None, description="Filter by priority"),
    limit: int = Query(100, description="Maximum number of issues to return")
):
    """
    List all triaged issues
    
    Returns all triaged issues with optional filtering by classification and priority.
    """
    try:
        triaged_issues = load_triaged_issues()
        
        # Apply filters
        if classification:
            triaged_issues = [
                issue for issue in triaged_issues
                if issue.get("classification") == classification
            ]
        
        if priority is not None:
            triaged_issues = [
                issue for issue in triaged_issues
                if issue.get("priority") == priority
            ]
        
        # Limit results
        triaged_issues = triaged_issues[:limit]
        
        return {
            "status": "success",
            "count": len(triaged_issues),
            "issues": triaged_issues
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
