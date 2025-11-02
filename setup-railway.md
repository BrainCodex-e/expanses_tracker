# Railway PostgreSQL Setup Guide

## Step 1: Create Railway Account
1. Go to **https://railway.app/**
2. **Sign up** with your GitHub account
3. **Verify** your account (they may ask for phone number for free tier)

## Step 2: Create PostgreSQL Database
1. Click **"New Project"**
2. Select **"Provision PostgreSQL"**
3. Wait for deployment to complete
4. Click on the **PostgreSQL service**

## Step 3: Get Database Connection
1. In PostgreSQL service, go to **"Variables"** tab
2. Copy the **DATABASE_URL** (should look like):
   ```
   postgresql://postgres:password@region.railway.app:5432/railway
   ```

## Step 4: Configure Render Environment Variables
1. Go to your Render dashboard: **https://dashboard.render.com/**
2. Find your **expanses_tracker** service
3. Go to **"Environment"** tab
4. Add these variables:
   - **DATABASE_URL**: `paste the Railway PostgreSQL URL here`
   - **USERS**: `your-username:your-secure-password,partner:another-password`
   - **SECRET_KEY**: `use output from ./generate-creds.sh`

## Step 5: Redeploy
1. Click **"Manual Deploy"** in Render
2. Wait for deployment to complete
3. Test that your data persists after 15+ minutes!

## Railway Free Tier Limits
- **500MB storage** (plenty for expense tracking)
- **$5 credit per month** (database uses ~$0.10-0.20/month)
- **Always-on** (never sleeps like Render apps)

## Verify It's Working
1. Add some expenses to your Render app
2. Wait 20+ minutes (let Render app sleep)
3. Visit app again - **your expenses should still be there!** 🎉