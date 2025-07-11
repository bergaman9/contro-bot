# Build the Docker image
Write-Host "Building Docker image..." -ForegroundColor Green
docker build -t contro-bot .

# Run the container
Write-Host "Running container..." -ForegroundColor Green
docker run -d `
  --name contro-bot `
  --env-file .env `
  -v ${PWD}/data:/app/data `
  -v ${PWD}/logs:/app/logs `
  -p 5000:5000 `
  contro-bot

Write-Host "Container started! Check logs with: docker logs contro-bot" -ForegroundColor Yellow 