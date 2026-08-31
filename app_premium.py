import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sqlite3
import os
import requests
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import json
import base64

# Optional libraries
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    Client = None

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Lilongwe Youth Tracker - DPP",
    page_icon="🇲🇼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CONFIG & SECRETS
# =============================================================================

DATABASE = 'youth_database.db'
DPP_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/3/3d/The_Democratic_Progressive_Party_Logo.svg"
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"

HF_TOKEN = os.environ.get('HF_TOKEN', '')
TWILIO_SID = os.environ.get('TWILIO_SID', '')
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN', '')
TWILIO_PHONE = os.environ.get('TWILIO_PHONE', '')

# =============================================================================
# DATABASE SETUP
# =============================================================================

def init_database():
    """Initialize database with enhanced schema"""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    cursor = conn.cursor()

    # Members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            attendance TEXT DEFAULT '',
            joined_date TEXT,
            role TEXT DEFAULT 'Member',
            achievements TEXT DEFAULT ''
        )
    ''')

    # Events table for future meetings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            location TEXT,
            description TEXT,
            created_at TEXT
        )
    ''')

    # Announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            created_at TEXT,
            priority TEXT DEFAULT 'normal'
        )
    ''')

    conn.commit()
    return conn

if 'conn' not in st.session_state:
    st.session_state.conn = init_database()

conn = st.session_state.conn

# =============================================================================
# LOGIN SETUP
# =============================================================================

USERS_FILE = 'users.yaml'
if not os.path.exists(USERS_FILE):
    config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'name': 'George Admin',
                    'password': stauth.Hasher().hash('pass123'),
                    'email': 'gmeya2041@gmail.com'
                }
            }
        },
        'cookie': {'name': 'youth_cookie', 'key': 'random_secret_key_2026', 'expiry_days': 30}
    }
    with open(USERS_FILE, 'w') as f:
        yaml.dump(config, f)

with open(USERS_FILE) as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def count_total_attendances(att_str):
    if not att_str:
        return 0
    return len([d.strip() for d in att_str.split(',') if d.strip()])

def get_future_message(total):
    if total >= 10:
        return "🏆 Leadership Material - Exceptional Commitment!"
    elif total >= 8:
        return "🌟 Rising Star - Keep Leading!"
    elif total >= 5:
        return "💚 Strong Foundation - Growing Strong!"
    elif total >= 3:
        return "💪 Building Momentum - Don't Stop!"
    else:
        return "💙 New Journey - We Believe in You!"

def get_badge_level(total):
    if total >= 15:
        return "💎 Diamond Member"
    elif total >= 10:
        return "🏆 Gold Member"
    elif total >= 5:
        return "🥈 Silver Member"
    elif total >= 3:
        return "🥉 Bronze Member"
    else:
        return "🌱 New Member"

def load_members():
    return pd.read_sql_query("SELECT * FROM members", conn)

def load_events():
    return pd.read_sql_query("SELECT * FROM events ORDER BY date DESC", conn)

def load_announcements():
    return pd.read_sql_query("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 5", conn)

def add_member(name, email, phone, role='Member'):
    cursor = conn.cursor()
    joined_date = datetime.now().strftime('%Y-%m-%d')
    cursor.execute(
        "INSERT INTO members (name, email, phone, joined_date, role) VALUES (?, ?, ?, ?, ?)",
        (name, email, phone, joined_date, role)
    )
    conn.commit()

def log_attendance(member_id, date_str):
    cursor = conn.cursor()
    cursor.execute("SELECT attendance FROM members WHERE id = ?", (member_id,))
    result = cursor.fetchone()
    if result:
        current = result[0] if result[0] else ''
        if date_str not in current:
            new_att = current + ',' + date_str if current else date_str
            cursor.execute("UPDATE members SET attendance = ? WHERE id = ?", (new_att, member_id))
            conn.commit()
            return True
    return False

def get_attendance_trend():
    """Get attendance trend over time"""
    df = load_members()
    all_dates = []
    for _, row in df.iterrows():
        if row['attendance']:
            dates = [d.strip() for d in row['attendance'].split(',') if d.strip()]
            all_dates.extend(dates)

    if not all_dates:
        return None

    date_counts = Counter(all_dates)
    sorted_dates = sorted(date_counts.items())

    return pd.DataFrame(sorted_dates, columns=['Date', 'Attendance'])

def create_animated_number(number, label, icon="📊", color="#4CAF50"):
    """Create an animated metric card"""
    return f"""
        <div style="
            background: linear-gradient(135deg, {color}22 0%, {color}11 100%);
            border-left: 4px solid {color};
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        " onmouseover="this.style.transform='translateY(-5px)'; this.style.boxShadow='0 8px 24px rgba(0,0,0,0.15)';"
           onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)';">
            <div style="font-size: 2.5rem; margin-bottom: 8px;">{icon}</div>
            <div style="font-size: 2.5rem; font-weight: bold; color: {color}; margin-bottom: 5px;">{number}</div>
            <div style="font-size: 0.9rem; color: #666; text-transform: uppercase; letter-spacing: 1px;">{label}</div>
        </div>
    """

# =============================================================================
# PREMIUM UI STYLES
# =============================================================================

def load_premium_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Playfair+Display:wght@700;900&display=swap');

        * {
            font-family: 'Poppins', sans-serif;
        }

        .main {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            background-attachment: fixed;
        }

        .stApp {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        }

        /* Animated Header */
        .hero-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 20px 60px rgba(102, 126, 234, 0.4);
            animation: slideDown 0.8s ease-out;
            position: relative;
            overflow: hidden;
        }

        .hero-header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 3s infinite;
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
            100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .hero-title {
            font-family: 'Playfair Display', serif;
            font-size: 3.5rem;
            font-weight: 900;
            color: white;
            text-align: center;
            margin: 0;
            text-shadow: 0 4px 12px rgba(0,0,0,0.3);
            animation: glow 2s ease-in-out infinite;
        }

        @keyframes glow {
            0%, 100% { text-shadow: 0 0 20px rgba(255,255,255,0.5), 0 0 40px rgba(255,255,255,0.3); }
            50% { text-shadow: 0 0 30px rgba(255,255,255,0.8), 0 0 60px rgba(255,255,255,0.5); }
        }

        .hero-subtitle {
            text-align: center;
            color: rgba(255,255,255,0.9);
            font-size: 1.3rem;
            margin-top: 15px;
            font-weight: 300;
            letter-spacing: 2px;
        }

        /* Premium Cards */
        .premium-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            transition: all 0.3s ease;
            animation: fadeInUp 0.6s ease-out;
        }

        .premium-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 16px 48px rgba(0,0,0,0.2);
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Glowing Buttons */
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 50px;
            padding: 15px 40px;
            font-weight: 600;
            font-size: 1rem;
            letter-spacing: 1px;
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
            text-transform: uppercase;
        }

        .stButton>button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            box-shadow: 0 12px 36px rgba(102, 126, 234, 0.6);
            transform: translateY(-3px);
        }

        /* Sidebar Styling */
        .css-1d391kg {
            background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
        }

        [data-testid="stSidebar"] .stSelectbox label {
            color: white;
            font-weight: 600;
        }

        /* Input Fields */
        .stTextInput>div>div>input, .stTextArea>div>div>textarea {
            border-radius: 12px;
            border: 2px solid #e0e0e0;
            padding: 12px;
            transition: all 0.3s ease;
        }

        .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        /* Achievement Badges */
        .badge {
            display: inline-block;
            padding: 8px 20px;
            border-radius: 50px;
            font-weight: 600;
            font-size: 0.9rem;
            margin: 5px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }

        .badge-diamond {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }

        .badge-gold {
            background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(255, 210, 0, 0.4);
        }

        .badge-silver {
            background: linear-gradient(135deg, #bdc3c7 0%, #95a5a6 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(189, 195, 199, 0.4);
        }

        .badge-bronze {
            background: linear-gradient(135deg, #cd7f32 0%, #b8860b 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(205, 127, 50, 0.4);
        }

        /* Progress Bar */
        .progress-bar {
            background: #e0e0e0;
            border-radius: 50px;
            height: 30px;
            overflow: hidden;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 50px;
            transition: width 1s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }

        /* Leaderboard */
        .leaderboard-item {
            background: white;
            padding: 20px;
            margin: 10px 0;
            border-radius: 15px;
            display: flex;
            align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            animation: slideInLeft 0.5s ease-out;
        }

        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .leaderboard-item:hover {
            transform: translateX(10px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }

        .rank-1 { border-left: 6px solid #FFD700; }
        .rank-2 { border-left: 6px solid #C0C0C0; }
        .rank-3 { border-left: 6px solid #CD7F32; }

        /* Floating Animation */
        .float {
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-10px); }
        }

        /* Celebration Effect */
        .celebrate {
            animation: celebrate 0.5s ease;
        }

        @keyframes celebrate {
            0%, 100% { transform: scale(1) rotate(0deg); }
            25% { transform: scale(1.1) rotate(-5deg); }
            75% { transform: scale(1.1) rotate(5deg); }
        }

        /* Dashboard Grid */
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        /* Notification Badge */
        .notification-badge {
            background: #ff4444;
            color: white;
            border-radius: 50%;
            padding: 5px 10px;
            font-size: 0.8rem;
            font-weight: bold;
            position: absolute;
            top: -10px;
            right: -10px;
            animation: bounce 1s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Glassmorphism Effect */
        .glass {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        /* Success Animation */
        .success-checkmark {
            display: inline-block;
            animation: scaleIn 0.5s ease;
        }

        @keyframes scaleIn {
            0% { transform: scale(0); }
            100% { transform: scale(1); }
        }

        /* Data Tables */
        .dataframe {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        /* Chart Container */
        .chart-container {
            background: white;
            padding: 25px;
            border-radius: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        </style>
    """, unsafe_allow_html=True)

# =============================================================================
# LOGIN SCREEN
# =============================================================================

login_result = authenticator.login(location='main')
if login_result:
    name, authentication_status, username = login_result
else:
    name, authentication_status, username = None, None, None

if authentication_status:
    load_premium_css()

    # Logout in sidebar
    authenticator.logout('🚪 Logout', 'sidebar')

    # =============================================================================
    # HERO HEADER
    # =============================================================================

    st.markdown(f"""
        <div class="hero-header">
            <h1 class="hero-title">🇲🇼 Lilongwe Youth Leadership Hub</h1>
            <p class="hero-subtitle">Democratic Progressive Party • State House Youth Division</p>
            <p style="text-align: center; color: rgba(255,255,255,0.8); margin-top: 10px;">
                Welcome back, <strong>{name}</strong>! 👋
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar
    st.sidebar.image(DPP_LOGO_URL, width=120)
    st.sidebar.title("🎯 Navigation")

    page = st.sidebar.selectbox("Choose Section", [
        "🏠 Home Dashboard",
        "👥 Members Directory",
        "➕ Add New Member",
        "✅ Attendance Check-in",
        "🏆 Leaderboard & Rankings",
        "📊 Analytics & Reports",
        "📅 Events Calendar",
        "📢 Announcements",
        "🤖 AI Leadership Coach",
        "📱 SMS Campaign",
        "💾 Export & Backup",
        "⚙️ Settings"
    ])

    # Quick Stats in Sidebar
    df = load_members()
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Quick Stats")
    st.sidebar.metric("Total Members", len(df))
    total_att = sum([count_total_attendances(row['attendance']) for _, row in df.iterrows()])
    st.sidebar.metric("Total Check-ins", total_att)
    avg_att = total_att / len(df) if len(df) > 0 else 0
    st.sidebar.metric("Avg Attendance", f"{avg_att:.1f}")

    # =============================================================================
    # HOME DASHBOARD
    # =============================================================================

    if page == "🏠 Home Dashboard":
        st.markdown("<h2 style='color: white; margin-top: 20px;'>📊 Live Dashboard</h2>", unsafe_allow_html=True)

        if len(df) > 0:
            # Animated Metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown(create_animated_number(len(df), "Total Members", "👥", "#667eea"), unsafe_allow_html=True)

            with col2:
                active = len([1 for _, row in df.iterrows() if count_total_attendances(row['attendance']) >= 5])
                st.markdown(create_animated_number(active, "Active Members", "⚡", "#f093fb"), unsafe_allow_html=True)

            with col3:
                st.markdown(create_animated_number(total_att, "Total Check-ins", "✅", "#4facfe"), unsafe_allow_html=True)

            with col4:
                stars = len([1 for _, row in df.iterrows() if count_total_attendances(row['attendance']) >= 10])
                st.markdown(create_animated_number(stars, "Star Leaders", "🌟", "#43e97b"), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Attendance Trend Chart
            trend_data = get_attendance_trend()
            if trend_data is not None and len(trend_data) > 0:
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.markdown("### 📈 Attendance Trend Over Time")

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=trend_data['Date'],
                    y=trend_data['Attendance'],
                    mode='lines+markers',
                    name='Attendance',
                    line=dict(color='#667eea', width=3),
                    marker=dict(size=10, color='#764ba2'),
                    fill='tozeroy',
                    fillcolor='rgba(102, 126, 234, 0.2)'
                ))

                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Poppins, sans-serif'),
                    height=400,
                    hovermode='x unified',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.05)')
                )

                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Top Performers
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.markdown("### 🏆 Top 5 Most Active Members")

                df['total_att'] = df['attendance'].apply(count_total_attendances)
                top_5 = df.nlargest(5, 'total_att')

                for idx, (_, row) in enumerate(top_5.iterrows(), 1):
                    badge = get_badge_level(row['total_att'])
                    rank_class = f"rank-{idx}" if idx <= 3 else ""

                    st.markdown(f"""
                        <div class="leaderboard-item {rank_class}">
                            <div style="font-size: 2rem; margin-right: 20px; min-width: 50px;">
                                {'🥇' if idx == 1 else '🥈' if idx == 2 else '🥉' if idx == 3 else f'#{idx}'}
                            </div>
                            <div style="flex: 1;">
                                <div style="font-weight: 700; font-size: 1.1rem;">{row['name']}</div>
                                <div style="color: #666; font-size: 0.9rem;">{badge}</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 1.5rem; font-weight: bold; color: #667eea;">{row['total_att']}</div>
                                <div style="font-size: 0.8rem; color: #999;">check-ins</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
                st.markdown("### 📊 Engagement Levels")

                # Pie chart of member levels
                levels = {
                    'Diamond (15+)': len([1 for _, row in df.iterrows() if count_total_attendances(row['attendance']) >= 15]),
                    'Gold (10-14)': len([1 for _, row in df.iterrows() if 10 <= count_total_attendances(row['attendance']) < 15]),
                    'Silver (5-9)': len([1 for _, row in df.iterrows() if 5 <= count_total_attendances(row['attendance']) < 10]),
                    'Bronze (3-4)': len([1 for _, row in df.iterrows() if 3 <= count_total_attendances(row['attendance']) < 5]),
                    'New (0-2)': len([1 for _, row in df.iterrows() if count_total_attendances(row['attendance']) < 3])
                }

                fig = go.Figure(data=[go.Pie(
                    labels=list(levels.keys()),
                    values=list(levels.values()),
                    hole=0.4,
                    marker=dict(colors=['#667eea', '#f7971e', '#95a5a6', '#cd7f32', '#e74c3c'])
                )])

                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=True,
                    legend=dict(font=dict(size=10))
                )

                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Recent Announcements
            announcements = load_announcements()
            if len(announcements) > 0:
                st.markdown("<div class='premium-card' style='margin-top: 20px;'>", unsafe_allow_html=True)
                st.markdown("### 📢 Latest Announcements")
                for _, ann in announcements.head(3).iterrows():
                    priority_icon = "🔴" if ann['priority'] == 'high' else "🟡" if ann['priority'] == 'medium' else "🟢"
                    st.markdown(f"""
                        <div style="padding: 15px; background: #f8f9fa; border-radius: 10px; margin: 10px 0;">
                            {priority_icon} <strong>{ann['title']}</strong><br>
                            <small style="color: #666;">{ann['content']}</small>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("🎯 No members yet! Start by adding your first member.")

    # =============================================================================
    # MEMBERS DIRECTORY
    # =============================================================================

    elif page == "👥 Members Directory":
        st.markdown("<h2 style='color: white;'>👥 Complete Members Directory</h2>", unsafe_allow_html=True)

        df = load_members()

        if len(df) > 0:
            # Search and Filter
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                search = st.text_input("🔍 Search members by name", placeholder="Type name...")
            with col2:
                min_attendance = st.number_input("Min Attendance", 0, 50, 0)
            with col3:
                role_filter = st.selectbox("Filter by Role", ["All", "Member", "Leader", "Admin"])

            # Filter dataframe
            filtered_df = df.copy()
            if search:
                filtered_df = filtered_df[filtered_df['name'].str.contains(search, case=False, na=False)]
            if role_filter != "All":
                filtered_df = filtered_df[filtered_df['role'] == role_filter]

            filtered_df['total_att'] = filtered_df['attendance'].apply(count_total_attendances)
            filtered_df = filtered_df[filtered_df['total_att'] >= min_attendance]

            st.markdown(f"<p style='color: white;'>Showing {len(filtered_df)} members</p>", unsafe_allow_html=True)

            # Display members as cards
            for _, row in filtered_df.iterrows():
                total = count_total_attendances(row['attendance'])
                badge = get_badge_level(total)
                message = get_future_message(total)

                st.markdown(f"""
                    <div class="premium-card" style="margin: 15px 0;">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div style="flex: 1;">
                                <h3 style="margin: 0; color: #333;">{row['name']}</h3>
                                <p style="color: #666; margin: 5px 0;">
                                    📧 {row['email'] if row['email'] else 'No email'} |
                                    📱 {row['phone'] if row['phone'] else 'No phone'} |
                                    👤 {row['role']}
                                </p>
                                <p style="color: #999; font-size: 0.9rem;">
                                    Joined: {row['joined_date'] if row['joined_date'] else 'N/A'}
                                </p>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 2rem; font-weight: bold; color: #667eea;">{total}</div>
                                <div style="font-size: 0.9rem; color: #666;">check-ins</div>
                                <div style="margin-top: 10px;">
                                    <span class="badge badge-{'diamond' if total >= 15 else 'gold' if total >= 10 else 'silver' if total >= 5 else 'bronze'}">{badge}</span>
                                </div>
                            </div>
                        </div>
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                            <div style="color: #667eea; font-weight: 600;">💬 {message}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if total >= 10:
                    st.balloons()
                    break

        else:
            st.info("No members in the directory yet.")

    # =============================================================================
    # ADD MEMBER
    # =============================================================================

    elif page == "➕ Add New Member":
        st.markdown("<h2 style='color: white;'>➕ Register New Member</h2>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)

        with st.form("add_member_form", clear_on_submit=True):
            st.markdown("### Member Information")

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name *", placeholder="John Banda")
                phone = st.text_input("Phone Number", placeholder="+265991234567")

            with col2:
                email = st.text_input("Email Address", placeholder="john@example.com")
                role = st.selectbox("Role", ["Member", "Leader", "Admin"])

            submitted = st.form_submit_button("✨ Add Member", use_container_width=True)

            if submitted:
                if name.strip():
                    add_member(name.strip(), email.strip(), phone.strip(), role)
                    st.success(f"🎉 Successfully added {name} to the youth group!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Name is required!")

        st.markdown("</div>", unsafe_allow_html=True)

        # Show recent additions
        df = load_members()
        if len(df) > 0:
            st.markdown("<div class='premium-card' style='margin-top: 20px;'>", unsafe_allow_html=True)
            st.markdown("### Recently Added Members")
            recent = df.tail(5)
            for _, row in recent.iterrows():
                st.markdown(f"- **{row['name']}** ({row['role']}) - Joined {row['joined_date']}")
            st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # ATTENDANCE CHECK-IN
    # =============================================================================

    elif page == "✅ Attendance Check-in":
        st.markdown("<h2 style='color: white;'>✅ Quick Attendance Check-in</h2>", unsafe_allow_html=True)

        today = datetime.now().strftime('%Y-%m-%d')

        st.markdown(f"<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown(f"### 📅 Today's Date: {datetime.now().strftime('%B %d, %Y')}")

        df = load_members()

        if len(df) > 0:
            if 'attendance_logged_today' not in st.session_state:
                st.session_state.attendance_logged_today = set()

            # Grid layout for checkboxes
            cols_per_row = 3
            rows = [df.iloc[i:i+cols_per_row] for i in range(0, len(df), cols_per_row)]

            for row_df in rows:
                cols = st.columns(cols_per_row)
                for idx, (_, member) in enumerate(row_df.iterrows()):
                    with cols[idx]:
                        current_attendance = member['attendance'] if member['attendance'] else ''
                        already_logged = today in current_attendance

                        if already_logged:
                            st.success(f"✅ {member['name']}")
                        else:
                            if st.checkbox(f"**{member['name']}**", key=f"attend_{member['id']}"):
                                if member['id'] not in st.session_state.attendance_logged_today:
                                    if log_attendance(member['id'], today):
                                        st.session_state.attendance_logged_today.add(member['id'])
                                        st.success("Logged!")
                                        st.rerun()

            logged_today = len([1 for _, row in df.iterrows() if today in (row['attendance'] or '')])

            st.markdown("---")
            st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
                    <h2 style="margin: 0;">📊 Today's Summary</h2>
                    <p style="font-size: 2rem; margin: 10px 0; font-weight: bold;">{logged_today} / {len(df)}</p>
                    <p>members checked in</p>
                    <div class="progress-bar" style="margin: 20px auto; max-width: 400px;">
                        <div class="progress-fill" style="width: {(logged_today/len(df)*100) if len(df) > 0 else 0}%;">
                            {int(logged_today/len(df)*100) if len(df) > 0 else 0}%
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        else:
            st.info("No members to check in yet!")

        st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # LEADERBOARD
    # =============================================================================

    elif page == "🏆 Leaderboard & Rankings":
        st.markdown("<h2 style='color: white;'>🏆 Member Leaderboard</h2>", unsafe_allow_html=True)

        df = load_members()

        if len(df) > 0:
            df['total_att'] = df['attendance'].apply(count_total_attendances)
            df = df.sort_values('total_att', ascending=False)

            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)

            for idx, (_, row) in enumerate(df.iterrows(), 1):
                badge = get_badge_level(row['total_att'])
                rank_class = f"rank-{idx}" if idx <= 3 else ""
                medal = '🥇' if idx == 1 else '🥈' if idx == 2 else '🥉' if idx == 3 else f"#{idx}"

                st.markdown(f"""
                    <div class="leaderboard-item {rank_class}" style="animation-delay: {idx*0.1}s;">
                        <div style="font-size: 2rem; margin-right: 20px; min-width: 60px; text-align: center;">
                            {medal}
                        </div>
                        <div style="flex: 1;">
                            <div style="font-weight: 700; font-size: 1.2rem;">{row['name']}</div>
                            <div style="color: #666; font-size: 0.9rem;">{badge} • {row['role']}</div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2rem; font-weight: bold; color: #667eea;">{row['total_att']}</div>
                            <div style="font-size: 0.8rem; color: #999;">check-ins</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Top performer celebration
            if len(df) > 0:
                top_performer = df.iloc[0]
                st.markdown(f"""
                    <div style="text-align: center; padding: 30px; margin-top: 20px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 20px; color: white;" class="celebrate">
                        <h2>👑 Top Performer of All Time 👑</h2>
                        <h1 style="font-size: 3rem; margin: 20px 0;">{top_performer['name']}</h1>
                        <p style="font-size: 1.5rem;">{top_performer['total_att']} Total Check-ins!</p>
                        <p style="font-size: 1.2rem; margin-top: 10px;">🎉 Absolute Legend! Keep inspiring others! 🎉</p>
                    </div>
                """, unsafe_allow_html=True)
                st.balloons()

        else:
            st.info("No members yet!")

    # =============================================================================
    # ANALYTICS
    # =============================================================================

    elif page == "📊 Analytics & Reports":
        st.markdown("<h2 style='color: white;'>📊 Advanced Analytics</h2>", unsafe_allow_html=True)

        df = load_members()

        if len(df) > 0:
            df['total_att'] = df['attendance'].apply(count_total_attendances)

            # Attendance distribution
            st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
            st.markdown("### 📈 Attendance Distribution")

            fig = px.histogram(df, x='total_att', nbins=10,
                             labels={'total_att': 'Number of Check-ins'},
                             color_discrete_sequence=['#667eea'])
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Poppins, sans-serif'),
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Role distribution
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.markdown("### 👥 Members by Role")
                role_counts = df['role'].value_counts()
                fig = px.pie(values=role_counts.values, names=role_counts.index,
                           color_discrete_sequence=px.colors.sequential.Plasma)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
                st.markdown("### ⭐ Top 10 Most Active")
                top_10 = df.nlargest(10, 'total_att')
                fig = px.bar(top_10, x='name', y='total_att',
                           color='total_att',
                           color_continuous_scale='Viridis',
                           labels={'total_att': 'Check-ins', 'name': 'Member'})
                fig.update_layout(showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Statistics summary
            st.markdown("<div class='premium-card' style='margin-top: 20px;'>", unsafe_allow_html=True)
            st.markdown("### 📊 Summary Statistics")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Average Attendance", f"{df['total_att'].mean():.1f}")
            with col2:
                st.metric("Median Attendance", f"{df['total_att'].median():.0f}")
            with col3:
                st.metric("Highest Attendance", f"{df['total_att'].max()}")
            with col4:
                st.metric("Attendance Rate", f"{(df['total_att'].sum() / (len(df) * 20) * 100):.0f}%")

            st.markdown("</div>", unsafe_allow_html=True)

        else:
            st.info("No data to analyze yet!")

    # =============================================================================
    # EVENTS CALENDAR
    # =============================================================================

    elif page == "📅 Events Calendar":
        st.markdown("<h2 style='color: white;'>📅 Upcoming Events</h2>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📋 View Events", "➕ Create Event"])

        with tab1:
            events = load_events()
            if len(events) > 0:
                for _, event in events.iterrows():
                    st.markdown(f"""
                        <div class="premium-card" style="margin: 15px 0;">
                            <h3 style="color: #667eea; margin: 0;">{event['title']}</h3>
                            <p style="color: #666; margin: 10px 0;">
                                📅 {event['date']} {f"• 🕐 {event['time']}" if event['time'] else ""}<br>
                                📍 {event['location'] if event['location'] else 'Location TBA'}
                            </p>
                            <p style="color: #333;">{event['description']}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No upcoming events scheduled.")

        with tab2:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            with st.form("create_event"):
                title = st.text_input("Event Title", placeholder="Youth Leadership Workshop")
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input("Date")
                with col2:
                    time = st.time_input("Time")
                location = st.text_input("Location", placeholder="State House Conference Hall")
                description = st.text_area("Description", placeholder="Event details...")

                if st.form_submit_button("🎯 Create Event", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO events (title, date, time, location, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, str(date), str(time), location, description, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    conn.commit()
                    st.success("Event created successfully! 🎉")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # ANNOUNCEMENTS
    # =============================================================================

    elif page == "📢 Announcements":
        st.markdown("<h2 style='color: white;'>📢 Announcements Board</h2>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📋 View Announcements", "➕ Create Announcement"])

        with tab1:
            announcements = load_announcements()
            if len(announcements) > 0:
                for _, ann in announcements.iterrows():
                    priority_color = "#ff4444" if ann['priority'] == 'high' else "#ffa500" if ann['priority'] == 'medium' else "#4CAF50"
                    priority_icon = "🔴" if ann['priority'] == 'high' else "🟡" if ann['priority'] == 'medium' else "🟢"

                    st.markdown(f"""
                        <div class="premium-card" style="border-left: 4px solid {priority_color}; margin: 15px 0;">
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <span style="font-size: 1.5rem; margin-right: 10px;">{priority_icon}</span>
                                <h3 style="margin: 0; color: #333;">{ann['title']}</h3>
                            </div>
                            <p style="color: #666; margin: 10px 0;">{ann['content']}</p>
                            <small style="color: #999;">Posted: {ann['created_at']}</small>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No announcements yet.")

        with tab2:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
            with st.form("create_announcement"):
                title = st.text_input("Announcement Title")
                content = st.text_area("Content", placeholder="Type your announcement...")
                priority = st.selectbox("Priority", ["normal", "medium", "high"])

                if st.form_submit_button("📣 Post Announcement", use_container_width=True):
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO announcements (title, content, priority, created_at) VALUES (?, ?, ?, ?)",
                        (title, content, priority, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    conn.commit()
                    st.success("Announcement posted! 📢")
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # AI COACH (continued from previous)
    # =============================================================================

    elif page == "🤖 AI Leadership Coach":
        st.markdown("<h2 style='color: white;'>🤖 AI Leadership Coach</h2>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)
        st.markdown("### 💬 Chat with Your AI Coach")
        st.markdown("Ask about youth leadership, community engagement, team building, and more!")

        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

        # Display chat
        for chat in st.session_state.chat_history:
            if chat['role'] == 'user':
                st.markdown(f"""
                    <div style="background: #667eea; color: white; padding: 15px; border-radius: 15px 15px 0 15px; margin: 10px 0 10px 50px;">
                        {chat['content']}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div style="background: #f8f9fa; color: #333; padding: 15px; border-radius: 15px 15px 15px 0; margin: 10px 50px 10px 0;">
                        🤖 {chat['content']}
                    </div>
                """, unsafe_allow_html=True)

        # Chat input
        question = st.chat_input("Ask me anything...")

        if question:
            st.session_state.chat_history.append({'role': 'user', 'content': question})

            if HF_TOKEN:
                headers = {"Authorization": f"Bearer {HF_TOKEN}"}
                payload = {
                    "inputs": f"<s>[INST] You are a youth leadership coach for the Democratic Progressive Party in Malawi. Provide helpful, motivational advice. {question} [/INST]",
                    "parameters": {"max_new_tokens": 250, "temperature": 0.7}
                }

                try:
                    with st.spinner("🤔 Thinking..."):
                        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)

                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, list) and len(result) > 0:
                            answer = result[0].get('generated_text', '')
                            if '[/INST]' in answer:
                                answer = answer.split('[/INST]')[-1].strip()
                            st.session_state.chat_history.append({'role': 'assistant', 'content': answer})
                            st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("⚠️ AI token not configured. Set HF_TOKEN in environment variables.")

        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # SMS CAMPAIGN
    # =============================================================================

    elif page == "📱 SMS Campaign":
        st.markdown("<h2 style='color: white;'>📱 SMS Engagement Campaign</h2>", unsafe_allow_html=True)

        df = load_members()

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🎯 Targeted Campaign", "📊 Campaign Stats"])

        with tab1:
            st.markdown("### Select Target Group")

            target_group = st.radio("Who to message:", [
                "🆕 New Members (0-2 check-ins)",
                "⚠️ At Risk (< 5 check-ins)",
                "⭐ Active Members (5+ check-ins)",
                "🏆 Top Performers (10+ check-ins)",
                "📢 Everyone"
            ])

            # Filter based on selection
            if "New Members" in target_group:
                targets = df[df['attendance'].apply(count_total_attendances) < 3]
            elif "At Risk" in target_group:
                targets = df[df['attendance'].apply(count_total_attendances) < 5]
            elif "Active" in target_group:
                targets = df[df['attendance'].apply(count_total_attendances) >= 5]
            elif "Top Performers" in target_group:
                targets = df[df['attendance'].apply(count_total_attendances) >= 10]
            else:
                targets = df

            st.info(f"📊 {len(targets)} members selected")

            # Message template
            templates = {
                "Encouragement": "Hi {name}! 🌟 You've attended {count} times. Keep up the amazing work! See you Sunday! 💚",
                "Reminder": "Hey {name}! 👋 We miss you at our meetings. Join us this Sunday! Your voice matters! 🇲🇼",
                "Appreciation": "Hi {name}! 🙏 Thank you for your {count} attendances! You're making a difference! Keep shining! ✨",
                "Custom": ""
            }

            template_choice = st.selectbox("Message Template", list(templates.keys()))
            message_text = st.text_area(
                "Message Content",
                value=templates[template_choice],
                height=100,
                help="Use {name} and {count} as placeholders"
            )

            if st.button("📤 Send Campaign", use_container_width=True):
                if TWILIO_AVAILABLE and TWILIO_SID and TWILIO_TOKEN:
                    client = Client(TWILIO_SID, TWILIO_TOKEN)
                    sent = 0
                    failed = 0

                    progress_bar = st.progress(0)

                    for idx, (_, row) in enumerate(targets.iterrows()):
                        if row['phone']:
                            total = count_total_attendances(row['attendance'])
                            message = message_text.replace('{name}', row['name']).replace('{count}', str(total))
                            try:
                                client.messages.create(
                                    body=message,
                                    from_=TWILIO_PHONE,
                                    to=row['phone']
                                )
                                sent += 1
                            except:
                                failed += 1

                        progress_bar.progress((idx + 1) / len(targets))

                    st.success(f"✅ Campaign complete! Sent: {sent}, Failed: {failed}")
                    st.balloons()
                else:
                    st.error("❌ Twilio not configured")

        with tab2:
            st.markdown("### 📊 SMS Campaign Statistics")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Members", len(df))
            with col2:
                with_phone = len(df[df['phone'].notna() & (df['phone'] != '')])
                st.metric("With Phone Numbers", with_phone)
            with col3:
                st.metric("Reachable", f"{(with_phone/len(df)*100):.0f}%")

        st.markdown("</div>", unsafe_allow_html=True)

    # =============================================================================
    # EXPORT
    # =============================================================================

    elif page == "💾 Export & Backup":
        st.markdown("<h2 style='color: white;'>💾 Data Export & Backup</h2>", unsafe_allow_html=True)

        df = load_members()

        if len(df) > 0:
            st.markdown("<div class='premium-card'>", unsafe_allow_html=True)

            # Prepare export
            df_export = df.copy()
            df_export['total_attendances'] = df_export['attendance'].apply(count_total_attendances)
            df_export['badge_level'] = df_export['total_attendances'].apply(get_badge_level)
            df_export['status_message'] = df_export['total_attendances'].apply(get_future_message)

            st.markdown("### 📊 Export Preview")
            st.dataframe(df_export, use_container_width=True)

            st.markdown("---")
            st.markdown("### 📥 Download Options")

            col1, col2, col3 = st.columns(3)

            with col1:
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f"youth_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            with col2:
                try:
                    from io import BytesIO
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Members')

                    st.download_button(
                        label="📊 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"youth_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                except:
                    st.info("Excel export unavailable")

            with col3:
                json_data = df_export.to_json(orient='records', indent=2)
                st.download_button(
                    label="🔧 Download JSON",
                    data=json_data,
                    file_name=f"youth_members_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

            # Backup info
            st.markdown("<div class='premium-card' style='margin-top: 20px;'>", unsafe_allow_html=True)
            st.markdown("### 💡 Backup Tips")
            st.markdown("""
            - 📅 **Export regularly** to keep backups of your data
            - ☁️ **Store in cloud** (Google Drive, Dropbox, etc.)
            - 🔒 **Keep secure** - contains member information
            - 📧 **Email backup** to yourself for safekeeping
            """)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No data to export yet")

    # =============================================================================
    # SETTINGS
    # =============================================================================

    elif page == "⚙️ Settings":
        st.markdown("<h2 style='color: white;'>⚙️ System Settings</h2>", unsafe_allow_html=True)

        st.markdown("<div class='premium-card'>", unsafe_allow_html=True)

        st.markdown("### 🔐 Account Settings")
        st.info(f"👤 Logged in as: **{name}** ({username})")

        st.markdown("---")
        st.markdown("### 📊 Database Information")

        df = load_members()
        events = load_events()
        announcements = load_announcements()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Members", len(df))
        with col2:
            st.metric("Total Events", len(events))
        with col3:
            st.metric("Total Announcements", len(announcements))

        st.markdown("---")
        st.markdown("### 🎨 Theme & Display")
        st.info("Current Theme: **Premium Dark Blue** 🌊")

        st.markdown("---")
        st.markdown("### ⚡ Quick Actions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📧 Contact Support", use_container_width=True):
                st.info("Email: gmeya2041@gmail.com")

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        **Lilongwe Youth Leadership Hub**
        Version 2.0 - Premium Edition

        Built with ❤️ for the Democratic Progressive Party
        State House Youth Division

        © 2026 - All Rights Reserved
        """)

        st.markdown("</div>", unsafe_allow_html=True)

    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style='text-align: center; color: rgba(255,255,255,0.6); padding: 30px; background: rgba(255,255,255,0.05); border-radius: 15px; margin-top: 50px;'>
            <p style='font-size: 1.1rem; font-weight: 600; margin-bottom: 10px;'>🇲🇼 Lilongwe Youth Leadership Hub 🇲🇼</p>
            <p>Under Democratic Progressive Party Leadership</p>
            <p style='font-size: 0.9rem; margin-top: 15px;'>Building Tomorrow's Leaders Today • Vision 2030</p>
            <p style='font-size: 0.8rem; margin-top: 20px; opacity: 0.7;'>Developed by George | Contact: gmeya2041@gmail.com</p>
        </div>
    """, unsafe_allow_html=True)

elif authentication_status == False:
    load_premium_css()
    st.markdown("""
        <div class="premium-card" style="max-width: 500px; margin: 100px auto; text-align: center;">
            <h2 style="color: #e74c3c;">❌ Authentication Failed</h2>
            <p>Username or password is incorrect</p>
            <p style="margin-top: 20px; color: #666;">
                <strong>Default Credentials:</strong><br>
                Username: <code>admin</code><br>
                Password: <code>pass123</code>
            </p>
        </div>
    """, unsafe_allow_html=True)

elif authentication_status == None:
    load_premium_css()
    st.markdown("""
        <div class="hero-header" style="max-width: 600px; margin: 50px auto;">
            <h1 class="hero-title" style="font-size: 2.5rem;">🇲🇼 Welcome!</h1>
            <p class="hero-subtitle" style="font-size: 1rem;">Lilongwe Youth Leadership Hub</p>
        </div>
        <div class="premium-card" style="max-width: 500px; margin: 30px auto; text-align: center;">
            <h3 style="color: #333;">Please login to continue</h3>
            <p style="margin-top: 20px; color: #666;">
                <strong>Default Credentials:</strong><br>
                Username: <code>admin</code><br>
                Password: <code>pass123</code>
            </p>
            <p style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 10px; font-size: 0.9rem;">
                💡 <strong>First time?</strong> Use the credentials above to access the system.
                Change your password after logging in for security.
            </p>
        </div>
    """, unsafe_allow_html=True)
