# Deploying ClassNote AI to the Internet

This guide explains how to deploy the React frontend on **Vercel** and the Python backend on **Render.com**. This is the most popular, fast, and free-tier-friendly hosting combination.

---

## Prerequisites
1. **GitHub Account:** Create a private or public repository on GitHub.
2. **Push Code to GitHub:**
   In your project root directory, run these commands to push your project:
   ```bash
   git init
   git add .
   git commit -m "Prepare for deployment"
   # Create a repo on github.com and copy the remote URL
   git remote add origin <your-github-repo-url>
   git branch -M main
   git push -u origin main
   ```

---

## Part 1: Deploying the Python Backend on Render

Render is a cloud hosting platform that can run your Python server directly from your GitHub repository.

1. **Sign up at [Render.com](https://render.com/)** using your GitHub account.
2. Click **New +** (top right) and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the Web Service settings:
   * **Name:** `classnote-backend`
   * **Region:** Choose the region closest to you (e.g., Singapore/Oregon).
   * **Branch:** `main`
   * **Root Directory:** `backend`
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python app_pure.py`
   * **Instance Type:** Select **Free** ($0/month).
5. Click **Advanced** and add the following **Environment Variables**:
   * `GEMINI_API_KEY`: `[YOUR_GEMINI_API_KEY_HERE]`
   * `MONGODB_URI`: `[YOUR_MONGODB_URI_HERE]`
   * `MONGO_DB_NAME`: `meeting_notes_db`
   * `USE_MOCK_SERVICES`: `false`
6. Click **Create Web Service**. 
7. Once deployment is complete, Render will give you a live URL, for example:
   `https://classnote-backend.onrender.com`

---

## Part 2: Deploying the React Frontend on Vercel

Vercel is the gold standard for hosting Vite React websites. It is 100% free and has a global CDN.

1. **Sign up at [Vercel.com](https://vercel.com/)** using your GitHub account.
2. Click **Add New** > **Project**.
3. Import your GitHub repository.
4. Configure the Project settings:
   * **Framework Preset:** `Vite` (Vercel will auto-detect it).
   * **Root Directory:** `frontend`
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
5. Expand the **Environment Variables** section and add:
   * **Key:** `VITE_API_URL`
   * **Value:** `https://your-backend-render-url.onrender.com/api` (Replace this with the exact Render live URL you got in Part 1 + `/api` at the end).
6. Click **Deploy**.
7. Vercel will build the frontend and provide you with your public deployment URL!

---

## Important Info: Chrome Microphone Policy on Live Sites
Google Chrome only allows microphone access on **secure origins (`https://`)**. Because Vercel and Render both provide secure `https://` URLs by default, speech recording will work perfectly without any warning blocks!
