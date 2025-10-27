# Summarization Service Integration Plan

## Overview

Instead of downloading and loading bearer transformers models in this data pipeline, we'll call an external summarization service.

## What the Service Should Provide

### API Endpoint
```
POST https://your-service.com/summarize
```

### Request Payload
```json
{
  "texts": [
    "Title 1: Summary of article 1 content...",
    "Title 2: Summary of article 2 content..."
  ],
  "max_length": 130,
  "min_length": 30
}
```

### Response Payload
```json
{
  "summary": "Summary text generated from the input texts"
}
```

### Error Handling
- Return HTTP 200 with `{"summary": ""}` for empty inputs
- Return HTTP 500 for service errors (pipeline will fall back)

## Current Implementation

Currently in `collector/summarizer.py`:
1. Loads model using `transformers.pipeline()`
2. Calls model locally with combined text
3. Returns summary

## Proposed Changes

### 1. Environment Variable
Add configurable service URL:
- `SUMMARIZATION_SERVICE_URL` (env var)
- Default to local fallback if not set

### 2. Update `collector/summarizer.py`
Add a `HttpSummarizer` class that:
- Makes HTTP requests to the service
- Falls back to local model if service unavailable
- Handles timeouts and errors gracefully

### 3. Update Dependencies
- Keep `transformers` as fallback
- Add `httpx` for async HTTP requests
- Remove torch from requirements (only in service)

### 4. Update GitHub Actions
- Remove Hugging Face cache step
- Remove timeout (should be much faster)
- Service call should be < 1 second vs 3+ minutes

## Benefits

1. **Fast runs**: No model download, just HTTP calls
2. **Clean separation**: ML models managed separately
3. **Scalable**: Service can handle many pipelines
4. **Easier updates**: Model improvements happen in one place
5. **Cost effective**: One service instance, many consumers

## Migration Strategy

1. Implement service with the API spec above
2. Deploy service (you handle this)
3. Update this pipeline to call the service
4. Test fallback behavior
5. Remove transformers dependency from this repo

## Fallback Behavior

If service is unavailable:
- Log warning
- Use simple extractive summary (first 280 chars)
- Pipeline continues to completion
- No failures unless all inputs are bad

