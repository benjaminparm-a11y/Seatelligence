# Restaurant Booking App

## Running in Production with Gunicorn

To start the Flask app in production mode using Gunicorn, run:

```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

- This will serve the app on port 5000, accessible from any network interface.
- Make sure you have installed all dependencies:

```bash
python3 -m pip install -r requirements.txt
```

## Deploying to Render

1. **Push to GitHub**
   - Initialize a Git repository and push your code:
     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     git remote add origin <your-github-repo-url>
     git push -u origin main
     ```

2. **Create Web Service on Render**
   - Go to [Render](https://render.com/) and sign in
   - Click **"New"** → **"Web Service"**
   - Connect your GitHub repository

3. **Configure Service**
   - **Build Command**: (leave default or use `pip install -r requirements.txt`)
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
   - **Environment Variables**: Add `SECRET_KEY` with a secure random string

4. **Deploy**
   - Click **"Create Web Service"**
   - Wait for the build to complete
   - Visit your Render URL (e.g., `https://your-app.onrender.com`)

5. **Optional: Custom Domain**
   - In Render dashboard → **"Settings"** → **"Custom Domains"**
   - Add your domain and configure DNS records as instructed

## Notes
- The file `wsgi.py` exposes the Flask app as `app` for Gunicorn import.
- If you use an app factory, ensure `wsgi.py` contains:
  ```python
  from app import create_app
  app = create_app()
  ```
  and use the same Gunicorn command above.
- Default login credentials:
  - Username: `admin` Password: `password123`
  - Username: `host` Password: `host123`
  - **Change these in production!**
