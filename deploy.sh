#!/bin/bash

echo "AI Ranker Deployment Script"
echo "==========================="

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "Error: flyctl is not installed. Please install it first:"
    echo "curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Deploy backend
echo ""
echo "Deploying Backend..."
echo "-------------------"
cd backend

# Create app if it doesn't exist
if ! flyctl status --app ai-ranker 2>/dev/null; then
    echo "Creating backend app..."
    flyctl apps create ai-ranker
fi

# Set secrets from .env file if it exists
if [ -f .env ]; then
    echo "Setting environment secrets..."
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
            # Remove quotes from value
            value="${value%\"}"
            value="${value#\"}"
            flyctl secrets set "$key=$value" --app ai-ranker
        fi
    done < .env
else
    echo "Warning: .env file not found. Please set secrets manually:"
    echo "flyctl secrets set KEY=value --app ai-ranker"
fi

# Create Postgres database if needed
echo "Setting up database..."
flyctl postgres create --name ai-ranker-db --region iad --initial-cluster-size 1 || true
flyctl postgres attach ai-ranker-db --app ai-ranker || true

# Deploy backend
echo "Deploying backend to Fly.io..."
flyctl deploy --app ai-ranker

# Get backend URL
BACKEND_URL=$(flyctl info --app ai-ranker -j | jq -r '.Hostname')
echo "Backend deployed at: https://$BACKEND_URL"

# Deploy frontend
echo ""
echo "Deploying Frontend..."
echo "--------------------"
cd ../frontend

# Create app if it doesn't exist
if ! flyctl status --app ai-ranker-frontend 2>/dev/null; then
    echo "Creating frontend app..."
    flyctl apps create ai-ranker-frontend
fi

# Set the backend URL
flyctl secrets set NEXT_PUBLIC_API_URL="https://$BACKEND_URL/api" --app ai-ranker-frontend

# Deploy frontend
echo "Deploying frontend to Fly.io..."
flyctl deploy --app ai-ranker-frontend

# Get frontend URL
FRONTEND_URL=$(flyctl info --app ai-ranker-frontend -j | jq -r '.Hostname')

echo ""
echo "==========================="
echo "Deployment Complete!"
echo "==========================="
echo "Frontend: https://$FRONTEND_URL"
echo "Backend API: https://$BACKEND_URL"
echo "API Docs: https://$BACKEND_URL/docs"
echo ""
echo "To view logs:"
echo "  Backend: flyctl logs --app ai-ranker"
echo "  Frontend: flyctl logs --app ai-ranker-frontend"