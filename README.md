# Lilongwe Youth Tracker - DPP

A Streamlit web application for managing and tracking youth member registrations, analytics, and messaging for the Democratic Progressive Party (DPP) in Lilongwe.

---

## 📌 Why uploading `files.zip` directly to GitHub didn't display the website

When you upload a `.zip` file (such as `files.zip`) directly to GitHub, GitHub stores it as a static downloadable file. GitHub and standard web hosting services cannot automatically unpack or run web applications directly inside a compressed `.zip` archive.

To fix this:
1. The code and configuration files have been **extracted directly into the repository root**:
   - `app.py`: Main Streamlit web application.
   - `requirements.txt`: Python dependencies needed to run the app.
   - `PREMIUM_FEATURES.md`: Feature overview and premium capabilities documentation.
2. The repository is now structured so cloud deployment services (like Streamlit Community Cloud) can automatically run it as a web app.

---

## 🚀 How to Run Locally

### Prerequisites
- Python 3.9 or higher

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/Youth-tracker-.git
   cd Youth-tracker-
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. Open `http://localhost:8501` in your web browser.

---

## 🌐 How to Deploy for Free as a Live Website

### Option 1: Deploy on Streamlit Community Cloud (Recommended & Easiest)

1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with your **GitHub account**.
2. Click **New App**.
3. Select your repository: `Youth-tracker-` (or `<your-username>/Youth-tracker-`).
4. Set **Branch** to `main` (or your default branch).
5. Set **Main file path** to `app.py`.
6. Click **Deploy!**

Within a minute, Streamlit will build your app and give you a public URL (e.g. `https://youth-tracker.streamlit.app`) to access your website.

### Option 2: Deploy on Render

1. Sign up on [Render.com](https://render.com/).
2. Create a new **Web Service** and connect your GitHub repository `Youth-tracker-`.
3. Set Environment to **Python 3**.
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
6. Click **Create Web Service**.

---

## 📄 Features

- **Dashboard & Analytics:** View key statistics, demographic breakdowns, and youth participation.
- **Member Management:** Add, update, search, and manage youth records.
- **Messaging Integration:** Integration options for SMS (Twilio) and AI assistance.
- **Export Data:** Export records to Excel / CSV format.

---

## 🔒 License

See `LICENSE` file for license details.
