# Setting Up Docker Hub Secrets for GitHub Actions

## Steps

### 1. Get Docker Hub Access Token

1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Give it a name like "weirdness-githubaction"
4. Copy the token (you won't see it again!)

### 2. Add to GitHub Repository Secrets

1. Go to: https://github.com/rl337/weirdness/settings/secrets/actions
2. Click "New repository secret"
3. Add:
   - Name: `DOCKERHUB_USERNAME`
   - Value: `rl337`
4. Click "Add secret"
5. Add another:
   - Name: `DOCKERHUB_TOKEN`
   - Value: (paste your Docker Hub token)
6. Click "Add secret"

### 3. Verify

The workflow will automatically:
- Build the container
- Test it
- Push to Docker Hub on successful pushes to main

### 4. Test

Make a small change to trigger the workflow:
```bash
echo "# Test build trigger" >> README.md
git add README.md
git commit -m "Test container build"
git push
```

Check results at: https://github.com/rl337/weirdness/actions

## Manual Workflow Trigger

You can also trigger manually:
1. Go to: https://github.com/rl337/weirdness/actions
2. Click "Build and Push Container"
3. Click "Run workflow"
4. Select branch and run

