# Hosting the Entire Project on Render.com (Single Web Service)

This guide explains how to host both the React frontend and the Python backend under a **single free Web Service** on Render.com. This completely avoids CORS issues, keeps everything under one domain name, and is 100% free.

---

## Step-by-Step Deployment Instructions

### 1. Connect to Render.com
1. Go to **[dashboard.render.com](https://dashboard.render.com/)** and log in with your GitHub account.
2. Click the blue **`New +`** button in the top-right corner.
3. Select **`Web Service`**.
4. Search for your repository **`classnote-ai`** and click **`Connect`**.

---

### 2. Configure the Render Web Service
Fill in the deployment form with the following settings:

* **Name:** `classnote-all-in-one`
* **Region:** Choose a region close to you (e.g., `Singapore` or `Oregon`).
* **Branch:** `main`
* **Root Directory:** *(Leave this blank! This is important so Render has access to both the frontend and backend folders).*
* **Runtime:** `Python 3`
* **Build Command:** Copy and paste this exact command:
  ```bash
  npm --prefix frontend install && npm --prefix frontend run build && pip install -r backend/requirements.txt
  ```
* **Start Command:** Copy and paste this exact command:
  ```bash
  python backend/app_pure.py
  ```
* **Instance Type:** Select **`Free`** ($0/month).

---

### 3. Configure Environment Variables
1. Scroll down the configuration page and click the **`Advanced`** button.
2. Click **`Add Environment Variable`** and input the following key-value pairs:
   * **Key:** `GEMINI_API_KEY` | **Value:** `[YOUR_GEMINI_API_KEY_HERE]`
   * **Key:** `MONGODB_URI` | **Value:** `[YOUR_MONGODB_URI_HERE]`
   * **Key:** `MONGO_DB_NAME` | **Value:** `meeting_notes_db`
   * **Key:** `USE_MOCK_SERVICES` | **Value:** `false`
3. Click the blue **`Create Web Service`** button at the bottom of the page.

---

### 4. Monitor and Launch
1. Render will open a console showing the live build log.
2. It will:
   * Install the React frontend packages.
   * Compile your React files into standard HTML/JS assets.
   * Install your Python requirements.
   * Start your python server on `0.0.0.0` bound to the allocated port.
3. Once the build log says `live` or `Build successful`, click your public link in the top-left corner (e.g., `https://classnote-all-in-one.onrender.com`).
4. **Congratulations!** Your entire web application is now live on the internet!
