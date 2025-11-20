# Railway Deployment Guide

This guide will walk you through deploying your Personal Finance Tracker to Railway.

## Prerequisites

- GitHub account
- Railway account (sign up at https://railway.app)
- Your code pushed to a GitHub repository

## Step 1: Prepare Your Repository

Your app is already configured for Railway! These files are already set up:

✅ `Procfile` - Tells Railway how to run your app
✅ `requirements.txt` - Lists all Python dependencies (including PostgreSQL support)
✅ `runtime.txt` - Specifies Python version
✅ `railway.json` - Railway configuration

## Step 2: Create a Railway Project

1. Go to https://railway.app and sign in with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your `personal-finance-tracker` repository
5. Railway will automatically detect it's a Flask app

## Step 3: Add PostgreSQL Database

1. In your Railway project dashboard, click **"New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will provision a PostgreSQL database and automatically set the `DATABASE_URL` environment variable
4. Your app will automatically use PostgreSQL instead of SQLite

## Step 4: Set Environment Variables

In your Railway project settings, go to **"Variables"** and add these:

### Required Variables:

```bash
# Generate a secure secret key
SECRET_KEY=<paste-secure-random-key-here>
FLASK_ENV=production
```

**Generate a secure SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Optional Variables (for email features):

```bash
# Email Configuration (if you want email functionality)
# Required for: Welcome emails, Password recovery, Future notifications
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=apikey
MAIL_PASSWORD=<your-sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
```

**Email Features (when configured):**
- ✉️ **Welcome emails** - Beautiful onboarding emails for new users
- 🔐 **Password recovery** - Secure password reset functionality
- 📬 **Future notifications** - Ready for additional features

**Recommended Email Providers:**
- **SendGrid** (100 emails/day free) - https://sendgrid.com
- **Mailgun** (100 emails/day free) - https://www.mailgun.com
- **Resend** (3,000 emails/month free) - https://resend.com

### Optional Variables (for currency conversion):

```bash
EXCHANGE_API_KEY=<your-api-key-from-exchangerate-api.com>
```

Get a free API key from: https://www.exchangerate-api.com

## Step 5: Initialize Database

After your app deploys, you need to create the database tables:

**Option A: Using Railway CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run database initialization
railway run python -c "from app import create_app; from models import db; app = create_app('production'); app.app_context().push(); db.create_all()"
```

**Option B: Add Initialization to app.py (Recommended)**

Add this to your `app.py` after `app = create_app()`:

```python
# Auto-create database tables on first deploy
with app.app_context():
    db.create_all()
    app.logger.info('Database tables created')
```

## Step 6: Verify Deployment

1. Railway will provide a URL like: `https://your-app.railway.app`
2. Click the URL to open your app
3. Try creating an account and logging in
4. Your data will persist in PostgreSQL!

## Step 7: Set Up Custom Domain (Optional)

1. In Railway project settings, go to **"Settings"** → **"Domains"**
2. Click **"Custom Domain"**
3. Add your domain (e.g., `financetracker.com`)
4. Update your DNS settings with the CNAME record provided by Railway
5. Railway automatically provisions SSL/HTTPS

## Troubleshooting

### Build Fails

**Check Logs:**
- Go to **"Deployments"** tab in Railway
- Click on the failed deployment
- Review the build logs

**Common Issues:**
- Missing dependencies in `requirements.txt`
- Python version mismatch (check `runtime.txt`)
- Syntax errors in code

### App Crashes After Deploy

**Check Runtime Logs:**
```bash
railway logs
```

**Common Issues:**
- `SECRET_KEY` not set
- Database not created (run `db.create_all()`)
- Missing environment variables

### Database Connection Issues

**Verify DATABASE_URL:**
```bash
railway variables
```

Make sure `DATABASE_URL` starts with `postgresql://`

If it starts with `postgres://`, Railway will automatically convert it.

## Monitoring & Maintenance

### View Logs
```bash
# View real-time logs
railway logs

# View logs for specific service
railway logs --service=web
```

### Database Backups

Railway automatically backs up your PostgreSQL database:
- Go to your database service
- Click **"Backups"** tab
- Download or restore backups as needed

### Update Deployment

Railway auto-deploys when you push to GitHub:
```bash
git add .
git commit -m "Update feature"
git push origin main
```

Railway will automatically:
1. Pull latest code
2. Install dependencies
3. Restart your app

## Cost Estimation

**Railway Free Tier:**
- $5 credit per month
- Enough for personal use with PostgreSQL
- No credit card required

**Estimated Usage:**
- Web service: ~$3/month
- PostgreSQL: ~$2/month
- **Total: ~$5/month (covered by free credit)**

For higher traffic, consider upgrading to Railway Pro ($20/month).

## Email Setup Guides

### SendGrid Setup
1. Sign up at https://sendgrid.com
2. Create an API key with "Mail Send" permissions
3. Add to Railway variables:
   ```bash
   MAIL_SERVER=smtp.sendgrid.net
   MAIL_PORT=587
   MAIL_USERNAME=apikey
   MAIL_PASSWORD=<your-api-key>
   ```

### Gmail Setup (Not Recommended for Production)
1. Enable 2FA on your Google account
2. Create an "App Password" for your app
3. Add to Railway variables:
   ```bash
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=<your-app-password>
   ```

## Next Steps

After deployment:

1. **Create your first account** - Navigate to `/register`
2. **Set up budget categories** - Go to Budget page
3. **Add transactions** - Start tracking your spending
4. **Explore YNAB principles** - Visit the FAQ page
5. **Set financial goals** - Create milestones

## Support

If you encounter issues:

1. Check Railway logs: `railway logs`
2. Review environment variables: `railway variables`
3. Check Railway status: https://status.railway.app
4. Railway Discord: https://discord.gg/railway

## Security Checklist

Before going to production:

- ✅ Set a strong, random `SECRET_KEY`
- ✅ Use PostgreSQL (not SQLite)
- ✅ Enable HTTPS (automatic with Railway)
- ✅ Keep dependencies updated
- ✅ Don't commit `.env` files to Git
- ✅ Use environment variables for secrets
- ✅ Regularly backup your database

## Additional Resources

- Railway Documentation: https://docs.railway.app
- Flask Deployment: https://flask.palletsprojects.com/en/2.3.x/deploying/
- PostgreSQL on Railway: https://docs.railway.app/databases/postgresql
- Custom Domains: https://docs.railway.app/deploy/exposing-your-app

---

Made with ❤️ by [Alex Raza](https://github.com/lizardcat)
