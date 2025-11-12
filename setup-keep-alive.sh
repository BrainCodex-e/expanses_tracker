#!/bin/bash
# Quick setup script for keep-alive solutions

echo "🚀 Keep-Alive Setup for Render"
echo "================================"
echo ""

# Detect current Render URL from git remote (if exists)
RENDER_URL=""
if git remote -v 2>/dev/null | grep -q "render"; then
    echo "✅ Detected Render deployment"
else
    echo "ℹ️  No Render remote detected (this is okay)"
fi

echo ""
echo "Choose your keep-alive solution:"
echo ""
echo "1. 🌐 UptimeRobot (Recommended - Free, Cloud-based)"
echo "2. ⏰ Cron Job (Requires computer always on)"
echo "3. 🐍 Python Script (Run on any machine)"
echo "4. 🤖 GitHub Actions (Cloud-based, free)"
echo "5. 💰 Upgrade Render to \$7/month (No keep-alive needed)"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo "📋 UptimeRobot Setup Steps:"
        echo "1. Go to https://uptimerobot.com (create free account)"
        echo "2. Click 'Add New Monitor'"
        echo "3. Settings:"
        echo "   - Monitor Type: HTTP(s)"
        echo "   - URL: https://your-app.onrender.com/status"
        echo "   - Monitoring Interval: 5 minutes"
        echo "4. Click 'Create Monitor'"
        echo ""
        echo "✅ Done! Your app will never sleep."
        echo ""
        read -p "Press Enter when you've set up UptimeRobot..."
        ;;
        
    2)
        echo ""
        read -p "Enter your Render app URL (e.g., https://your-app.onrender.com): " APP_URL
        
        # Update the cron script
        sed -i "s|https://your-app.onrender.com|$APP_URL|g" keep_alive_cron.sh 2>/dev/null || \
        sed -i '' "s|https://your-app.onrender.com|$APP_URL|g" keep_alive_cron.sh
        
        echo ""
        echo "📋 Cron Job Setup:"
        echo ""
        echo "Add this line to your crontab (crontab -e):"
        echo ""
        echo "*/14 * * * * $(pwd)/keep_alive_cron.sh >> /tmp/keep_alive.log 2>&1"
        echo ""
        echo "Or run this command to add it automatically:"
        echo "(crontab -l 2>/dev/null; echo \"*/14 * * * * $(pwd)/keep_alive_cron.sh >> /tmp/keep_alive.log 2>&1\") | crontab -"
        echo ""
        read -p "Add to crontab now? (y/n): " add_cron
        
        if [ "$add_cron" = "y" ]; then
            (crontab -l 2>/dev/null; echo "*/14 * * * * $(pwd)/keep_alive_cron.sh >> /tmp/keep_alive.log 2>&1") | crontab -
            echo "✅ Cron job added!"
        fi
        ;;
        
    3)
        echo ""
        read -p "Enter your Render app URL (e.g., https://your-app.onrender.com): " APP_URL
        
        # Check if requests is installed
        if ! python3 -c "import requests" 2>/dev/null; then
            echo "📦 Installing requests library..."
            pip install requests
        fi
        
        echo ""
        echo "📋 Python Script Setup:"
        echo ""
        echo "To run the keep-alive script:"
        echo ""
        echo "  APP_URL=\"$APP_URL\" python3 keep_alive.py"
        echo ""
        echo "To run in background:"
        echo ""
        echo "  APP_URL=\"$APP_URL\" nohup python3 keep_alive.py &"
        echo ""
        read -p "Start now? (y/n): " start_now
        
        if [ "$start_now" = "y" ]; then
            export APP_URL="$APP_URL"
            echo "🚀 Starting keep-alive script..."
            echo "Press Ctrl+C to stop"
            python3 keep_alive.py
        fi
        ;;
        
    4)
        echo ""
        read -p "Enter your Render app URL (e.g., https://your-app.onrender.com): " APP_URL
        
        # Update GitHub Actions workflow
        if [ -f ".github/workflows/keep-alive.yml" ]; then
            echo ""
            echo "📋 GitHub Actions Setup:"
            echo ""
            echo "1. Go to GitHub repo → Settings → Secrets → Actions"
            echo "2. Click 'New repository secret'"
            echo "3. Name: APP_URL"
            echo "4. Value: $APP_URL"
            echo "5. Click 'Add secret'"
            echo ""
            echo "6. Commit and push the workflow file:"
            echo "   git add .github/workflows/keep-alive.yml"
            echo "   git commit -m 'Add keep-alive GitHub Action'"
            echo "   git push origin main"
            echo ""
            echo "✅ GitHub Actions will ping your app every 14 minutes!"
            echo ""
            read -p "Push to GitHub now? (y/n): " push_now
            
            if [ "$push_now" = "y" ]; then
                git add .github/workflows/keep-alive.yml
                git commit -m "Add keep-alive GitHub Action"
                git push origin main
                echo "✅ Pushed to GitHub!"
                echo ""
                echo "Now add the APP_URL secret in GitHub Settings."
            fi
        else
            echo "❌ GitHub Actions workflow file not found!"
        fi
        ;;
        
    5)
        echo ""
        echo "💰 Upgrading Render:"
        echo ""
        echo "Benefits:"
        echo "  ✅ No cold starts (always awake)"
        echo "  ✅ Better performance (1GB RAM, faster CPU)"
        echo "  ✅ Background workers allowed"
        echo ""
        echo "Cost: \$7/month per service"
        echo ""
        echo "To upgrade:"
        echo "1. Go to your Render dashboard"
        echo "2. Select your app"
        echo "3. Click 'Settings' → 'Change Instance Type'"
        echo "4. Choose 'Starter' (\$7/month)"
        echo ""
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📚 For more details, see: infrastructure/keep_alive_service.md"
echo ""
echo "✅ Setup complete!"
