#!/bin/bash

echo "AI Ranker Deployment Script (Using Existing Accounts)"
echo "======================================================"

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "Error: flyctl is not installed. Please install it first:"
    echo "curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f backend/.env ]; then
    echo "Error: backend/.env file not found!"
    echo "Please create it from the example:"
    echo "  cp backend/.env.example backend/.env"
    echo "  Then add your API keys and credentials"
    exit 1
fi

echo "Using existing Fly.io, Upstash, and LangSmith accounts..."
echo ""

# Deploy backend
echo "Deploying Backend..."
echo "-------------------"
cd backend

# Launch backend app (will prompt for app name if it doesn't exist)
echo "Launching backend app..."
if ! flyctl status --app ai-ranker 2>/dev/null; then
    flyctl launch \
        --name ai-ranker \
        --region iad \
        --no-deploy \
        --dockerfile Dockerfile
else
    echo "App ai-ranker already exists, skipping creation..."
fi

# Create Postgres database if needed
echo ""
echo "Setting up PostgreSQL database..."
read -p "Do you want to create a new Postgres database? (y/n): " create_db
if [[ $create_db == "y" ]]; then
    flyctl postgres create --name ai-ranker-db --region iad --initial-cluster-size 1
    flyctl postgres attach ai-ranker-db --app ai-ranker
else
    echo "Skipping database creation. Make sure DATABASE_URL is set in secrets."
fi

# Set secrets from .env file
echo ""
echo "Setting environment secrets from .env file..."
while IFS='=' read -r key value; do
    # Skip comments and empty lines
    if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
        # Remove quotes from value
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        
        # Skip DATABASE_URL if using Fly Postgres (it's auto-set)
        if [[ "$key" == "DATABASE_URL" ]] && [[ $create_db == "y" ]]; then
            echo "Skipping DATABASE_URL (auto-configured by Fly Postgres)"
        else
            echo "Setting $key..."
            flyctl secrets set "$key=$value" --app ai-ranker --stage
        fi
    fi
done < .env

# Deploy secrets
echo "Deploying secrets..."
flyctl secrets deploy --app ai-ranker

# Deploy backend
echo ""
echo "Deploying backend to Fly.io..."
flyctl deploy --app ai-ranker

# Get backend URL
BACKEND_URL=$(flyctl info --app ai-ranker -j | jq -r '.Hostname')
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL="ai-ranker.fly.dev"
fi
echo "Backend deployed at: https://$BACKEND_URL"

# Deploy frontend
echo ""
echo "Deploying Frontend..."
echo "--------------------"
cd ../frontend

# Launch frontend app
echo "Launching frontend app..."
if ! flyctl status --app ai-ranker-frontend 2>/dev/null; then
    flyctl launch \
        --name ai-ranker-frontend \
        --region iad \
        --no-deploy \
        --dockerfile Dockerfile
else
    echo "App ai-ranker-frontend already exists, skipping creation..."
fi

# Set the backend URL for frontend
echo "Setting backend URL for frontend..."
flyctl secrets set NEXT_PUBLIC_API_URL="https://$BACKEND_URL/api" --app ai-ranker-frontend

# Deploy frontend
echo "Deploying frontend to Fly.io..."
flyctl deploy --app ai-ranker-frontend

# Get frontend URL
FRONTEND_URL=$(flyctl info --app ai-ranker-frontend -j | jq -r '.Hostname')
if [ -z "$FRONTEND_URL" ]; then
    FRONTEND_URL="ai-ranker-frontend.fly.dev"
fi

echo ""
echo "======================================================"
echo "Deployment Complete!"
echo "======================================================"
echo "Frontend: https://$FRONTEND_URL"
echo "Backend API: https://$BACKEND_URL"
echo "API Docs: https://$BACKEND_URL/docs"
echo ""
echo "LangSmith Traces: https://smith.langchain.com/o/$(grep LANGCHAIN_PROJECT backend/.env | cut -d'=' -f2 | tr -d '"')"
echo ""
echo "To view logs:"
echo "  Backend: flyctl logs --app ai-ranker"
echo "  Frontend: flyctl logs --app ai-ranker-frontend"
echo ""
echo "To check app status:"
echo "  flyctl status --app ai-ranker"
echo "  flyctl status --app ai-ranker-frontend"