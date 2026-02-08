# TriageAI - IssuePilot

A FastAPI-based GitHub issue triage system that automatically classifies and prioritizes issues.

## Features

- **Fetch Issues**: Automatically fetch issues from any GitHub repository
- **Classification**: Uses TF-IDF to classify issues as `bug`, `feature`, or `docs`
- **Priority Assignment**: Assigns priority 1-5 based on keywords and issue age
- **JSON Storage**: Stores triaged issues in JSON format
- **REST API**: Three main endpoints for syncing, triaging, and listing issues

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. (Optional) Set GitHub token for higher API rate limits:
```bash
export GITHUB_TOKEN="your_github_token"
```

## Running the Server

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Root - `/`
Get API information

```bash
curl http://localhost:8000/
```

### 2. Sync Issues - `POST /sync`
Fetch and triage issues from a GitHub repository

```bash
curl -X POST "http://localhost:8000/sync?owner=facebook&repo=react&state=open"
```

Parameters:
- `owner` (required): Repository owner
- `repo` (required): Repository name
- `state` (optional): Issue state - `open`, `closed`, or `all` (default: `open`)

### 3. Triage Single Issue - `POST /triage`
Manually triage a specific issue

```bash
curl -X POST "http://localhost:8000/triage?number=123&title=Fix+bug+in+login&body=The+login+feature+is+broken"
```

Parameters:
- `number` (required): Issue number
- `title` (required): Issue title
- `body` (optional): Issue body
- `created_at` (optional): Issue creation date in ISO format

### 4. List Triaged Issues - `GET /list`
List all triaged issues with optional filtering

```bash
curl "http://localhost:8000/list"
curl "http://localhost:8000/list?classification=bug&priority=5"
```

Parameters:
- `classification` (optional): Filter by classification (`bug`, `feature`, `docs`)
- `priority` (optional): Filter by priority (1-5)
- `limit` (optional): Maximum number of results (default: 100)

## Classification Logic

The system uses TF-IDF (Term Frequency-Inverse Document Frequency) to classify issues:

- **Bug**: Keywords like error, crash, broken, exception, fix
- **Feature**: Keywords like add, new, enhancement, request, implement
- **Docs**: Keywords like documentation, readme, guide, tutorial, example

## Priority Assignment

Priority (1-5) is calculated based on:

1. **Keywords**:
   - Priority 5: critical, urgent, security, crash, data loss, blocking
   - Priority 4: important, high, regression, broken
   - Priority 3: moderate, normal, enhancement
   - Priority 2: minor, low, improvement
   - Priority 1: trivial, cosmetic, typo

2. **Age**: Issues older than 3-6 months get priority boost

## Data Storage

Triaged issues are stored in `triaged_issues.json` with the following structure:

```json
[
  {
    "number": 123,
    "title": "Fix login bug",
    "body": "The login feature is broken",
    "created_at": "2024-01-01T00:00:00Z",
    "state": "open",
    "url": "https://github.com/owner/repo/issues/123",
    "classification": "bug",
    "priority": 4,
    "triaged_at": "2024-01-15T12:00:00"
  }
]
```

## Interactive API Documentation

FastAPI provides automatic interactive documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Workflow

1. Start the server:
```bash
python main.py
```

2. Sync issues from a repository:
```bash
curl -X POST "http://localhost:8000/sync?owner=fastapi&repo=fastapi&state=open"
```

3. List triaged issues:
```bash
curl "http://localhost:8000/list?classification=bug&priority=5"
```

4. Manually triage an issue:
```bash
curl -X POST "http://localhost:8000/triage?number=999&title=Add+new+feature&body=Request+for+OAuth+support"
```

## License

MIT