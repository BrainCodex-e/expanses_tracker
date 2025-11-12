#!/bin/bash
# Quick setup script for Supabase + Render hybrid deployment

echo "🚀 Supabase + Render Setup Script"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here

# Optional: Keep DATABASE_URL for gradual migration
# DATABASE_URL=your-render-postgres-url

# App Configuration
SECRET_KEY=your-secret-key-here
USERS=erez:password,lia:password,mom:password,dad:password
SESSION_COOKIE_SECURE=0
EOF
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env and add your Supabase credentials"
else
    echo "✅ .env file already exists"
fi

# Check if supabase is in requirements.txt
if ! grep -q "supabase" requirements.txt; then
    echo ""
    echo "📦 Adding Supabase to requirements.txt..."
    echo "supabase==2.3.4" >> requirements.txt
    echo "✅ Added supabase==2.3.4 to requirements.txt"
else
    echo "✅ Supabase already in requirements.txt"
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit .env and add your Supabase URL and Anon Key"
echo "   - Get these from: https://app.supabase.com/project/_/settings/api"
echo ""
echo "2. Run database migration in Supabase SQL Editor:"
echo "   - Copy content from: supabase_schema.sql"
echo "   - Paste in: https://app.supabase.com/project/_/sql"
echo ""
echo "3. Enable Realtime on expenses table:"
echo "   - Go to: https://app.supabase.com/project/_/database/publications"
echo "   - Enable Realtime for 'expenses' table"
echo ""
echo "4. Test locally:"
echo "   python app.py"
echo ""
echo "5. Deploy to Render:"
echo "   - Add SUPABASE_URL and SUPABASE_ANON_KEY to Render env vars"
echo "   - git push origin main"
echo ""
echo "📖 Full guide: See HYBRID_SETUP.md"
