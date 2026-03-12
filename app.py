import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
# import sqlite3
# import bcrypt
from datetime import datetime
from scipy import stats


# Page configuration
st.set_page_config(
    page_title="Listening Data Explorer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB_PATH = "spotify_analysis.db"



### SQL / AUTH LAYER 

# def get_connection():
#     """Establish and return a connection to the SQLite database"""
#     return sqlite3.connect(DB_PATH, check_same_thread=False)

# def init_db():
#     """Initialize database tables for users and user actions if they don't exist"""
#     conn = get_connection()
#     cur = conn.cursor()
    
#     # Users table
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT UNIQUE NOT NULL,
#             password TEXT NOT NULL
#         )
#     """)
    
#     # User actions table with details column
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS user_actions (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT NOT NULL,
#             action TEXT NOT NULL,
#             details TEXT,
#             ts TEXT NOT NULL
#         )
#     """)
    
#     # Ensure details column exists
#     cur.execute("PRAGMA table_info(user_actions)")
#     columns = [row[1] for row in cur.fetchall()]
#     if "details" not in columns:
#         cur.execute("ALTER TABLE user_actions ADD COLUMN details TEXT")
    
#     conn.commit()
#     conn.close()

# def create_user(username, password):
#     """
#     Create a new user account with bcrypt-hashed password. 
#     Returns True if successful, False if username already exists.
#     """

#     conn = get_connection()
#     cur = conn.cursor()
#     try:
#         hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#         cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
#                     (username, hashed_password))
#         conn.commit()
#         return True
#     except sqlite3.IntegrityError:
#         return False
#     finally:
#         conn.close()

# def verify_user(username, password):
#     """    Verify user login credentials against stored bcrypt hash
#     Returns True if credentials are valid, False otherwise.
#     """

#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute("SELECT password FROM users WHERE username = ?", (username,))
#     row = cur.fetchone()
#     conn.close()
    
#     if row is None:
#         return False
    
#     return bcrypt.checkpw(password.encode('utf-8'), row[0])

# def log_action(username, action, details=None):
#     """Log user actions to the database for tracking purposes"""
#     conn = get_connection()
#     cur = conn.cursor()
#     ts = datetime.utcnow().isoformat()
#     cur.execute(
#         "INSERT INTO user_actions (username, action, details, ts) VALUES (?, ?, ?, ?)",
#         (username, action, details, ts)
#     )
#     conn.commit()
#     conn.close()



### LOGIN / REGISTER UI

# def show_login_page():
#     """Display login and registration interface"""
#     st.title("🔐 Login to Spotify Wrapped Analysis")
    
#     tab_login, tab_register = st.tabs(["Sign in", "Register"])
    
#     with tab_login:
#         st.subheader("Sign in")
#         login_user = st.text_input("Username", key="login_user")
#         login_pass = st.text_input("Password", type="password", key="login_pass")
#         if st.button("Login"):
#             if verify_user(login_user, login_pass):
#                 st.session_state["logged_in"] = True
#                 st.session_state["username"] = login_user
#                 log_action(login_user, "login_success")
#                 st.success(f"Welcome, {login_user}!")
#                 st.rerun()
#             else:
#                 st.error("Invalid username or password")
    
#     with tab_register:
#         st.subheader("Create new account")
#         new_user = st.text_input("New username", key="new_user")
#         new_pass = st.text_input("New password", type="password", key="new_pass")
#         if st.button("Register"):
#             if not new_user or not new_pass:
#                 st.error("Username and password cannot be empty")
#             else:
#                 ok = create_user(new_user, new_pass)
#                 if ok:
#                     st.success("Account created! You can now log in.")
#                 else:
#                     st.error("Username already exists")



### DATA PROCESSING FUNCTIONS

@st.cache_data
def load_demo_data():
    """Load pre-processed demo data"""
    df = pd.read_parquet('demo_data/streams_all.parquet')
    df_valid = pd.read_parquet('demo_data/streams_valid.parquet')
    return df, df_valid


@st.cache_data
def load_and_process_user_data(uploaded_files):
    """Load user's multiple JSON files (extended streaming data) and process them"""
    df_list = []
    for file in uploaded_files:
        df = pd.read_json(file)
        df_list.append(df)
    
    df = pd.concat(df_list, ignore_index=True)
    
    # Remove IP and country columns
    df = df.drop(columns=['ip_addr', 'conn_country'], errors='ignore')
    
    # Convert timestamp - make sure 'ts' column exists
    if 'ts' in df.columns:
        df['timestamp'] = pd.to_datetime(df['ts'])
    else:
        raise ValueError("Column 'ts' not found in the data. Please check your JSON files.")
    
    # Filter 2025 data only
    df = df[df['timestamp'].dt.year == 2025]
    df = df.drop(columns=['ts'], errors='ignore')
    
    # Rename columns
    cols_to_rename = {
        'master_metadata_track_name': 'track_name',
        'master_metadata_album_artist_name': 'artist_name',
        'master_metadata_album_album_name': 'album_name'
    }
    df = df.rename(columns=cols_to_rename)
    
    # Convert to minutes
    df.insert(1, 'minutes_played', df['ms_played'] / 60000)
    df = df.drop(columns=['ms_played'], errors='ignore')
    
    # Remove podcasts and audiobooks
    df = df[(df['audiobook_uri'].isnull()) & (df['spotify_episode_uri'].isnull())]
    
    # Drop podcast/audiobook columns
    cols_to_remove = ["episode_name", "episode_show_name", "spotify_episode_uri",
                      "audiobook_title", "audiobook_uri", "audiobook_chapter_uri", 
                      "audiobook_chapter_title"]
    df = df.drop(columns=cols_to_remove, errors='ignore')
    
    # Remove duplicates
    df = df.drop_duplicates(keep='first')
    df = df.reset_index(drop=True)
    
    # Add temporal features
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['weekday'] = df['timestamp'].dt.weekday
    df['month'] = df['timestamp'].dt.month_name()
    
    # Time period categorization
    def categorize_time_period(hour):
        """Categorize hour of day feature into time periods"""
        if 6 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 18:
            return 'Afternoon'
        elif 18 <= hour < 24:
            return 'Evening'
        else:
            return 'Night'
    
    df['time_period'] = df['hour'].apply(categorize_time_period)
    
    # Platform categorization
    def categorize_platform(platform):
        """Categorize platform into simplified types"""
        if platform == 'android':
            return 'Mobile'
        elif platform in ['windows', 'osx']:
            return 'Desktop'
        else:
            return 'Other'
    
    df['platform_type'] = df['platform'].apply(categorize_platform)
    
    # Add valid stream flag (30 seconds threshold)
    df['is_valid_stream'] = df['minutes_played'] >= 0.5
    df_valid = df[df['is_valid_stream']].copy()

    
    return df, df_valid


### VISUALIZATION FUNCTIONS ###

def show_overview(df, df_valid):
    """Display basic stats overview"""
    st.header("Overview Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Plays", f"{len(df):,}")
        st.metric("Valid Streams (Plays ≥30s)", f"{len(df_valid):,}")
        
    with col2:
        total_hours = df_valid['minutes_played'].sum() / 60
        st.metric("Total Listening Time", f"{total_hours:.1f} hours")
        avg_daily = total_hours / df_valid['timestamp'].dt.date.nunique()
        st.metric("Avg Daily Listening", f"{avg_daily:.2f} hours")
        
    with col3:
        st.metric("Unique Artists", f"{df_valid['artist_name'].nunique():,}")
        st.metric("Unique Tracks", f"{df_valid['track_name'].nunique():,}")
    

def show_top_content(df, df_valid):
    """Display top 10 artists/tracks/albums"""
    st.header("Top Content")
    
    # Filter selection
    use_filtered_data = st.checkbox(
        "Apply 30-second filter (recommended)",
        value=True,
        key="filter_top_content",
        help="Only include streams ≥30 seconds"
    )
    
    df_to_use = df_valid if use_filtered_data else df    


    # TOP ARTISTS
    st.markdown("---")
    st.subheader("Top 10 Artists by Listening Time")
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")

    artist_stats = df_to_use.groupby('artist_name').agg({
        'track_name': 'count',
        'minutes_played': 'sum'
    }).rename(columns={'track_name': 'play_count'})

    artist_stats['hours_played'] = artist_stats['minutes_played'] / 60
    top_artists = artist_stats.nlargest(10, 'hours_played').reset_index()
    
    # Top artists visualization with plotly
    fig = px.bar(top_artists, 
        x='hours_played',
        y="artist_name",
        orientation='h', 
        color='hours_played', 
        color_continuous_scale='algae', # plotly's built-in color scale: https://plotly.com/python/builtin-colorscales/
        labels={'hours_played': 'Total Hours Played', 'artist_name': 'Artist'})
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'},
        hovermode="y",
        coloraxis_showscale=False # remove colorbar legend
    )

    fig.update_traces(
        texttemplate='%{x:.1f}h', 
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Total listening time: %{x:.1f}h<br>Number of plays: %{customdata[0]}",
        customdata=top_artists[['play_count']]
    )

    st.plotly_chart(fig, use_container_width=True)


    # TOP TRACKS
    st.markdown("---")
    st.subheader("Top 10 Tracks by Play Count")
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")

    track_stats = df_to_use.groupby(['track_name', 'artist_name']).agg({
        'timestamp': 'count',
        'minutes_played': 'sum'
    }).rename(columns={'timestamp': 'play_count'})
    top_tracks = track_stats.nlargest(10, 'play_count').reset_index()
    
    
    # Top tracks visualization with plotly
    fig = px.bar(top_tracks, 
        x='play_count',
        y=top_tracks.apply(lambda row: f"{row['track_name']}\n({row['artist_name']})", axis=1),
        orientation='h', 
        color='play_count', 
        color_continuous_scale='Peach', # plotly's built-in color scale: https://plotly.com/python/builtin-colorscales/
        labels={'play_count': 'Number of Plays', 'y': 'Track (Artist)'})
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'},
        hovermode="y",
        coloraxis_showscale=False # remove colorbar legend
    )

    fig.update_traces(
        texttemplate='%{x} plays',
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Number of plays: %{x}<br>Total listening time: %{customdata[0]:.1f}h",
        customdata=top_tracks[['minutes_played']].values / 60
    )

    st.plotly_chart(fig, use_container_width=True)
    

    # TOP ALBUMS
    st.markdown("---")
    st.subheader("Top 10 Albums by Listening Time")
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")

    album_stats = df_to_use.groupby(['album_name', 'artist_name']).agg({
        'timestamp': 'count',
        'minutes_played': 'sum'
    }).rename(columns={'timestamp': 'play_count'})
    album_stats['hours_played'] = album_stats['minutes_played'] / 60
    top_albums = album_stats.nlargest(10, 'hours_played').reset_index()

    # Top albums visualization with plotly
    fig = px.bar(top_albums,
        x='hours_played',
        y=top_albums.apply(lambda row: f"{row['album_name']}\n({row['artist_name']})", axis=1),
        orientation='h', 
        color='hours_played', 
        color_continuous_scale='Teal', # plotly's built-in color scale: https://plotly.com/python/builtin-colorscales/
        labels={'hours_played': 'Total Hours Played', 'y': 'Album (Artist)'})
    
    fig.update_layout(yaxis={'categoryorder':'total ascending'},
        hovermode="y",
        coloraxis_showscale=False # remove colorbar legend
    )

    fig.update_traces(
        texttemplate='%{x:.1f}h', 
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Total listening time: %{x:.1f}h<br>Number of plays: %{customdata[0]}",
        customdata=top_albums[['play_count']].values
    )

    st.plotly_chart(fig, use_container_width=True)


def show_temporal_analysis(df, df_valid):
    """Display temporal patterns"""
    st.header("Temporal Analysis")
    
    # Filter selection
    use_filtered_data = st.checkbox(
        "Apply 30-second filter (recommended)",
        value=True,
        key="filter_temporal",
        help="Only include streams ≥30 seconds"
    )
    
    df_to_use = df_valid if use_filtered_data else df
    
        
    # BY HOUR OF DAY
    st.markdown('---')
    st.subheader("Listening Patterns by Hour of Day")
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")
    
    hourly_stats = df_to_use.groupby('hour').agg({
        'minutes_played': 'sum',
        'track_name': 'count'
    }).rename(columns={'track_name': 'play_count'}).reset_index()

    hourly_stats['hours_played'] = hourly_stats['minutes_played'] / 60
    hourly_stats['avg_minutes_per_play'] = hourly_stats['minutes_played'] / hourly_stats['play_count']
    

    fig = px.bar(
        hourly_stats,
        x='hour',
        y='hours_played',
        labels={'hour': 'Hour of Day', 'hours_played': 'Total Hours Played'},
        color_discrete_sequence=['#1DB954'] # Spotify's green color
    )
    
    # Add average line
    avg_hours = hourly_stats['hours_played'].mean()
    fig.add_shape(
        type="line",
        x0=-0.5, x1=23.5,
        y0=avg_hours, y1=avg_hours,
        line=dict(color="Red", width=2, dash="dash"),
    )

    # Add annotation for average line
    fig.add_annotation(
        x=23, y=avg_hours,
        text=f"Avg: {avg_hours:.1f}h",
        showarrow=False,
        yshift=10,
        font=dict(color="Red",weight="bold")
    )

    # Customize axes and layout
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=0, dtick=1), # Print all hours from 0 to 23
        yaxis_title="Total Hours Played",
        hovermode="x",
        margin=dict(l=20, r=20, t=50, b=20)
    )

    # Add custom hover data for play count
    fig.update_traces(
        hovertemplate="<b>Hour of the Day: %{x}h</b><br>Total listening time during the year: %{y:.1f}h<br>Number of plays: %{customdata[0]}",
        customdata=hourly_stats[['play_count']]
    )

    st.plotly_chart(fig, use_container_width=True)    


    # BY DAY OF WEEK
    st.markdown('---')
    st.subheader("Listening Patterns by Day of Week")
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    weekly_stats = df_to_use.groupby('day_of_week').agg({
        'minutes_played': 'sum',
        'track_name': 'count'
    }).rename(columns={'track_name': 'play_count'})

    weekly_stats['hours_played'] = weekly_stats['minutes_played'] / 60
    weekly_stats = weekly_stats.reindex(day_order)

    day_counts = df_to_use.groupby('day_of_week')['date'].nunique().reindex(day_order)
    avg_hours = weekly_stats['hours_played'] / day_counts
    
    # Data preparation for heatmap
    hourly_weekly = df_to_use.groupby(['weekday', 'hour'])['minutes_played'].sum() / 60
    hourly_weekly = hourly_weekly.unstack(fill_value=0)

    # Ensure lines correspond to days of week in correct order
    heatmap_data = hourly_weekly.reindex(range(7), fill_value=0)

    fig = make_subplots(
        rows=1, cols=2, 
        subplot_titles=('Average Daily Listening', 'Listening Activity Heatmap'),
        horizontal_spacing=0.15
    )

    # Bar Chart (left)
    fig.add_trace(
        go.Bar(
            x=day_order,
            y=avg_hours,
            text=avg_hours.apply(lambda x: f'{x:.2f}h'),
            textposition='outside',
            marker_color=['#1DB954' if day in ['Saturday', 'Sunday'] else '#1ED760' for day in day_order],
            name="Avg Hours",
            hovertemplate="<b>%{x}</b><br>Average: %{y:.2f}h<extra></extra>"
        ),
        row=1, col=1
    )

    # 2. Heatmap (right)
    fig.add_trace(
        go.Heatmap(
            z=heatmap_data.values,
            x=list(range(24)),
            y=day_order,
            colorscale='YlGn',
            colorbar=dict(title="Hours", x=1.05),
            name="Activity",
            hovertemplate="Day: %{y}<br>Hour: %{x}h<br>Time: %{z:.2f}h<extra></extra>"
        ),
        row=1, col=2
    )

    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    fig.update_xaxes(title_text="Day", row=1, col=1)
    fig.update_yaxes(title_text="Average Hours per Day", row=1, col=1)
    fig.update_xaxes(title_text="Hour of Day", tickmode='linear', dtick=2, row=1, col=2)

    st.plotly_chart(fig, use_container_width=True)


    # DAILY TRENDS
    st.markdown('---')
    st.subheader("Daily Listening Trends Over 2025")    
    if use_filtered_data:
        st.caption(f"Analysis based on valid streams only (≥30s) — {len(df_valid):,} plays")
    else:
        st.caption(f"Analysis based on all plays (including <30s) — {len(df):,} plays")

    daily_stats = df_to_use.groupby('date')['minutes_played'].sum().reset_index()
    daily_stats['hours_played'] = daily_stats['minutes_played'] / 60

    fig = px.bar(
        daily_stats,
        x='date',
        y='hours_played',
        labels={'date': 'Date', 'hours_played': 'Hours Played'},
        color_discrete_sequence=['#1DB954'] # Spotify Green color
    )

    # Calculate average for this section
    avg_hours_daily = daily_stats['hours_played'].mean()
    
    fig.add_shape(
        type="line",
        x0=daily_stats['date'].min(), 
        x1=daily_stats['date'].max(),
        y0=avg_hours_daily, 
        y1=avg_hours_daily,
        line=dict(color="Red", width=2, dash="dash")
    )

    # 4. Annotation for average line
    fig.add_annotation(
        x=daily_stats['date'].max(), 
        y=avg_hours_daily,
        text=f"Avg: {avg_hours_daily:.1f}h",
        showarrow=False, 
        yshift=10, 
        xanchor="right",
        font=dict(color="Red", weight="bold")
    )
    # 5. Customization of Tooltip (info bubble)
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>Listening time: %{y:.2f}h<extra></extra>" 
    )

    st.plotly_chart(fig, use_container_width=True)


def show_valid_streams_filtering(df, df_valid):
    """Display valid streams criteria and filtering impact"""
    st.header("Valid Streams Filtering")
    st.markdown("""
    **Spotify's 30-Second Threshold:** A track play is counted as a stream only if it lasted at least 30 seconds.
    This criterion is documented by Spotify and is used to calculate streaming royalties and Wrapped statistics.
    
    This section analyzes the distribution of play durations and the impact of this filtering criterion on the data.
    """)
    
    st.markdown("---")

    ### General Statistics and Distribution of Play Durations
    # Display summary statistics
    st.subheader("Play Duration Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**All Plays:**")
        st.dataframe(df['minutes_played'].describe(), use_container_width=True)
    
    with col2:
        st.markdown("**Valid Plays (≥30s):**")
        st.dataframe(df_valid['minutes_played'].describe(), use_container_width=True)

    # Valid vs Invalid distribution    
    valid_count = len(df_valid)
    invalid_count = len(df) - valid_count
    
    # Create two-column layout with plotly
    col1, col2 = st.columns(2)

    with col1:
        # Plot 1: Histogram of play durations with 30s threshold line
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=df['minutes_played'],
            nbinsx=100,
            marker=dict(color='#1DB954', line=dict(color='black', width=1)),
            name='Play Durations',
            hovertemplate='%{x:.2f}min<br>Count: %{y}<extra></extra>'
        ))
        
        # Add vertical line at 30-second threshold (0.5 minutes)
        fig.add_vline(
            x=0.5,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text="30-second threshold",
            annotation_position="top right"
        )
        
        fig.update_layout(
            title='Play Duration Distribution',
            xaxis_title='Minutes Played',
            yaxis_title='Frequency',
            height=500,
            template='plotly_white',
            showlegend=False,
            xaxis=dict(range=[0, 5], gridcolor='lightgray'),  # Focus on first 5 minutes
            yaxis=dict(gridcolor='lightgray')
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Plot 2: Valid streams vs All plays
        colors = ['#1DB954', '#FF6B6B']
        counts = [valid_count, invalid_count]
        categories = ['Valid (≥30s)', 'Invalid (<30s)']
        percentages = [valid_count/len(df)*100, invalid_count/len(df)*100]
        
        fig = go.Figure(go.Bar(
            x=categories,
            y=counts,
            marker=dict(color=colors, line=dict(color='black', width=1)),
            text=[f'{count:,}<br>({pct:.1f}%)' for count, pct in zip(counts, percentages)],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Count: %{y:,}<br>Percentage: %{customdata:.1f}%<extra></extra>',
            customdata=percentages
        ))
        
        fig.update_layout(
            title='Share of Valid vs Invalid Plays',
            yaxis_title='Number of Plays',
            height=500,
            template='plotly_white',
            showlegend=False,
            yaxis=dict(gridcolor='lightgray')
        )
        
        st.plotly_chart(fig, use_container_width=True)


    # Interpretation section
    st.subheader("Interpretation")
    st.markdown("""
    **Observation:** Nearly two-thirds of all plays fall below the 30-second threshold, representing a substantial 
    share of very short interactions that do not necessarily reflect meaningful listening behavior.
    
    **Possible reasons for short plays (following the user):**
    - **Active exploration:** Users browsing playlists or albums to find specific tracks
    - **Music discovery:** Quickly sampling new tracks before deciding to listen fully
    - **Library management:** Organizing and sorting music generates many brief interactions
    - **Skipping behavior:** Moving past tracks that don't match the current mood or context
    
    For most users, the 30-second threshold effectively filters out unintentional plays, navigation artifacts, 
    and exploratory behavior while retaining genuine listening activity.
    """)

    
    st.markdown("---")
    
    # Impact comparison on Top 10 rankings
    st.subheader("Impact of 30-Second Threshold on Top Rankings")
    st.markdown("""
    This visualization shows how the 30-second filtering criterion affects the top 10 tracks and artists by play count.
    The percentage reduction indicates how many plays were filtered out for each item.
    """)
    
    # Calculate track statistics
    track_stats_valid = df_valid.groupby(['track_name', 'artist_name']).size()
    
    # Get top 10 tracks based on valid streams
    top_10_tracks = track_stats_valid.nlargest(10).index.tolist()
    track_labels = [f"{track}\n({artist})" for track, artist in top_10_tracks]
    track_all_counts = [df[(df['track_name'] == t) & (df['artist_name'] == a)].shape[0] for t, a in top_10_tracks]
    track_valid_counts = [df_valid[(df_valid['track_name'] == t) & (df_valid['artist_name'] == a)].shape[0] for t, a in top_10_tracks]
    
    # Calculate artist statistics
    artist_stats_valid = df_valid.groupby('artist_name').size()
    
    # Get top 10 artists based on valid streams
    top_10_artists = artist_stats_valid.nlargest(10).index.tolist()
    artist_all_counts = [df[df['artist_name'] == a].shape[0] for a in top_10_artists]
    artist_valid_counts = [df_valid[df_valid['artist_name'] == a].shape[0] for a in top_10_artists]
    
    # Create vertical subplots with plotly
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Top 10 Tracks by Play Count', 'Top 10 Artists by Play Count'),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # TOP PLOT: Top 10 Tracks
    # Calculate differences for annotations
    track_diff_pcts = [((all_c - valid_c) / all_c) * 100 for all_c, valid_c in zip(track_all_counts, track_valid_counts)]
    
    # Add bars for all plays
    fig.add_trace(
        go.Bar(
            x=track_all_counts,
            y=track_labels,
            orientation='h',
            name='All Plays (including <30s)',
            marker=dict(color='#FF6B6B', line=dict(color='black', width=1)),
            text=[f'{c:,}' for c in track_all_counts],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>All Plays: %{x:,}<extra></extra>',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add bars for valid streams
    fig.add_trace(
        go.Bar(
            x=track_valid_counts,
            y=track_labels,
            orientation='h',
            name='Valid Streams (≥30s)',
            marker=dict(color='#1DB954', line=dict(color='black', width=1)),
            text=[f'{c:,}' for c in track_valid_counts],
            textposition='inside',
            insidetextanchor='end',
            hovertemplate='<b>%{y}</b><br>Valid Streams: %{x:,}<br>Reduction: %{customdata:.0f}%<extra></extra>',
            customdata=track_diff_pcts,
            showlegend=True
        ),
        row=1, col=1
    )
    
    # BOTTOM PLOT: Top 10 Artists
    # Calculate differences for annotations
    artist_diff_pcts = [((all_c - valid_c) / all_c) * 100 for all_c, valid_c in zip(artist_all_counts, artist_valid_counts)]
    
    # Add bars for all plays
    fig.add_trace(
        go.Bar(
            x=artist_all_counts,
            y=top_10_artists,
            orientation='h',
            name='All Plays (including <30s)',
            marker=dict(color='#FF6B6B', line=dict(color='black', width=1)),
            text=[f'{c:,}' for c in artist_all_counts],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>All Plays: %{x:,}<extra></extra>',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add bars for valid Streams
    fig.add_trace(
        go.Bar(
            x=artist_valid_counts,
            y=top_10_artists,
            orientation='h',
            name='Valid Streams (≥30s)',
            marker=dict(color='#1DB954', line=dict(color='black', width=1)),
            text=[f'{c:,}' for c in artist_valid_counts],
            textposition='inside',
            insidetextanchor='end',
            hovertemplate='<b>%{y}</b><br>Valid Streams: %{x:,}<br>Reduction: %{customdata:.0f}%<extra></extra>',
            customdata=artist_diff_pcts,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title_text='Impact of 30-Second Threshold: All Plays vs Valid Streams Comparison',
        title_font_size=18,
        height=1200,
        template='plotly_white',
        barmode='overlay',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    # Update axes
    fig.update_xaxes(title_text='Number of Plays', gridcolor='lightgray', row=1, col=1)
    fig.update_xaxes(title_text='Number of Plays', gridcolor='lightgray', row=2, col=1)
    fig.update_yaxes(autorange='reversed', row=1, col=1)
    fig.update_yaxes(autorange='reversed', row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def show_hypothesis_pareto(df_to_use, use_filtered_data):
    """Display visualization for Hypothesis 1 (Pareto Principle): 
    A small number of artists dominate listening time"""
    st.subheader("Pareto Principle")
    st.markdown("**Assumption:** *A small number of artists accounts for a large proportion of total listening time*")
    
    # Calculate artist time share
    artist_time = df_to_use.groupby('artist_name')['minutes_played'].sum().sort_values(ascending=False)
    total_time = artist_time.sum()
    artist_time_pct = (artist_time / total_time) * 100
    cumulative_pct = artist_time_pct.cumsum()
    
    # Find 80% threshold
    artists_for_80 = (cumulative_pct <= 80).sum() + 1
    pct_of_total = (artists_for_80 / len(artist_time)) * 100
    diff_from_pareto = abs(pct_of_total - 20)
    TIGHT_MARGIN = 5
    LOOSE_MARGIN = 10
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 10 artists
        top_10_artists = artist_time_pct.head(10)
        colors = ['#1ED760' if i < artists_for_80 else '#1DB954' for i in range(len(top_10_artists))]
        hours = [artist_time[idx] / 60 for idx in top_10_artists.index]
        hover_text = [f'{artist}<br>{pct:.2f}%<br>{h:.1f}h' for artist, pct, h in zip(top_10_artists.index, top_10_artists.values, hours)]
        
        fig = go.Figure(go.Bar(
            x=top_10_artists.values,
            y=top_10_artists.index,
            orientation='h',
            marker=dict(color=colors, line=dict(color='black', width=1)),
            text=[f'{pct:.2f}% ({h:.1f}h)' for pct, h in zip(top_10_artists.values, hours)],
            textposition='outside',
            hovertext=hover_text,
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title='Top 10 Artists by Listening Time',
            xaxis_title='Share of Total Listening Time (%)',
            yaxis=dict(autorange='reversed'),
            height=500,
            showlegend=False,
            template='plotly_white',
            xaxis=dict(gridcolor='lightgray')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Cumulative distribution
        n_artists = len(artist_time)
        x_pos = list(range(n_artists))
        
        fig = go.Figure()
        
        # Add shaded area for top artists
        fig.add_trace(go.Scatter(
            x=list(range(artists_for_80)) + [artists_for_80, 0],
            y=[100] * artists_for_80 + [0, 0],
            fill='toself',
            fillcolor='rgba(0, 255, 0, 0.2)',
            line=dict(width=0),
            name=f'Top {artists_for_80} artists',
            hoverinfo='skip',
            showlegend=True
        ))
        
        # Add cumulative curve
        fig.add_trace(go.Scatter(
            x=x_pos,
            y=cumulative_pct.values,
            mode='lines',
            line=dict(color='#FF6B6B', width=3),
            fill='tonexty',
            fillcolor='rgba(255, 107, 107, 0.3)',
            name='Cumulative %',
            hovertemplate='Artist rank: %{x}<br>Cumulative: %{y:.1f}%<extra></extra>'
        ))
        
        # Add horizontal line at 80%
        fig.add_hline(y=80, line_dash="dash", line_color="red", line_width=2,
                      annotation_text="80% threshold", annotation_position="right")
        
        # Add vertical line at threshold artist
        fig.add_vline(x=artists_for_80-1, line_dash="dash", line_color="red", line_width=2)
        
        # Add annotation
        fig.add_annotation(
            x=artists_for_80,
            y=80,
            text=f'{artists_for_80} artists<br>({pct_of_total:.1f}%)',
            showarrow=True,
            arrowhead=6,
            arrowcolor='red',
            arrowwidth=2,
            ax=60,
            ay=60,
            bgcolor='yellow',
            bordercolor='red',
            borderwidth=2,
            font=dict(color='red', size=11)
        )
        
        fig.update_layout(
            title='Cumulative Distribution: Pareto Principle',
            xaxis_title='Number of Artists (Ranked by Listening Time)',
            yaxis_title='Cumulative Percentage (%)',
            height=500,
            template='plotly_white',
            xaxis=dict(range=[0, n_artists]),
            yaxis=dict(range=[0, 105]),
            legend=dict(x=0.7, y=0.1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    # Results
    # st.info(f"**Result:** {artists_for_80} artists ({pct_of_total:.1f}% of total) account for 80% of listening time")

    st.subheader("Results Summary")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Artists for 80% Time", f"{artists_for_80}")
    col_b.metric("Share of Total Artists", f"{pct_of_total:.1f}%")
    col_c.metric("Difference from 20% Pareto", f"{diff_from_pareto:.1f}%")

    if diff_from_pareto <= TIGHT_MARGIN:
        st.success("✅ **Hypothesis CONFIRMED:** Result is close to the 20% Pareto benchmark, concentration is in the 15-25% range")
    elif diff_from_pareto <= LOOSE_MARGIN:
        st.warning("⚠️ **Hypothesis PARTIALLY CONFIRMED:** Concentration is in the 10–30% range, but not very close to 20%")
    else:
        st.error("❌ **Hypothesis NOT CONFIRMED:** Concentration is far from the 20% Pareto benchmark")


def show_hypothesis_time_of_day(df_to_use, use_filtered_data):
    """Display visualization for Hypothesis 2 (Time of Day Patterns): 
    Evening listening is higher than morning listening"""
    st.subheader("Time of Day Patterns")
    st.markdown("**Assumption:** *Listening activity is higher during evening hours (18:00-23:59) than during early morning hours (6:00-11:59)*")
    
    # Calculate hourly and period stats
    hourly_stats = df_to_use.groupby('hour').agg({
        'minutes_played': 'sum',
        'track_name': 'count'
    }).rename(columns={'track_name': 'play_count'})
    hourly_stats['hours_played'] = hourly_stats['minutes_played'] / 60
    
    period_order = ['Night', 'Morning', 'Afternoon', 'Evening']
    period_stats = df_to_use.groupby('time_period')['minutes_played'].sum() / 60
    period_stats = period_stats.reindex(period_order)
    
    morning_hours = period_stats['Morning']
    evening_hours = period_stats['Evening']
    ratio = morning_hours / evening_hours

    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Plot 1: Hourly distribution
        period_colors_map = {
            'Night': '#4472C4',
            'Morning': '#FDB813',
            'Afternoon': '#FF6B35',
            'Evening': '#9B59B6'
        }
        
        fig = go.Figure()
        
        # Add background regions for time periods
        period_ranges = [(0, 6, 'Night'), (6, 12, 'Morning'), (12, 18, 'Afternoon'), (18, 24, 'Evening')]
        for start, end, period in period_ranges:
            fig.add_vrect(
                x0=start, x1=end,
                fillcolor=period_colors_map[period],
                opacity=0.1,
                layer='below',
                line_width=0,
                annotation_text=period,
                annotation_position='top left'
            )
        
        # Add line trace
        fig.add_trace(go.Scatter(
            x=hourly_stats.index,
            y=hourly_stats['hours_played'],
            mode='lines+markers',
            line=dict(color="#9E9E9E", width=2),
            marker=dict(size=8, color="#9E9E9E"),
            fill='tonexty',
            fillcolor="rgba(0, 0, 0, 0.2)",
            name='Hours Played',
            hovertemplate='Total Hours: %{y:.1f}h<extra></extra>'
        ))
        
        fig.update_layout(
            title='Listening Time by Moment of the Day',
            xaxis_title='Hour of Day',
            yaxis_title='Total Hours Played',
            height=500,
            template='plotly_white',
            xaxis=dict(tickmode='linear', tick0=0, dtick=2),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    

    with col2:
        # Plot 2: Period comparison
        period_colors = ['#4472C4', '#FDB813', '#FF6B35', '#9B59B6']
        percentages = [(h / period_stats.sum()) * 100 for h in period_stats.values]
        hover_text = [f'{period}<br>{hours:.1f}h<br>({pct:.1f}%)' for period, hours, pct in zip(period_order, period_stats.values, percentages)]
        
        fig = go.Figure(go.Bar(
            x=period_order,
            y=period_stats.values,
            marker=dict(color=period_colors, line=dict(color='black', width=1)),
            text=[f'{h:.1f}h<br>({p:.1f}%)' for h, p in zip(period_stats.values, percentages)],
            textposition='outside',
            hovertext=hover_text,
            hoverinfo='text'
        ))
        
        fig.update_layout(
            title='Total Listening Time by Time Period',
            xaxis_title='Time Period',
            yaxis_title='Total Hours Played',
            height=500,
            template='plotly_white',
            showlegend=False,
            yaxis=dict(gridcolor='lightgray')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    

    # Results
    st.markdown("---")
    st.subheader("Results Summary")
    dominant   = "Morning dominates" if ratio > 1 else "Evening dominates"
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Morning listening (6:00-11:59)", f"{morning_hours:.1f}h")
    col_b.metric("Evening listening (18:00-23:59)", f"{evening_hours:.1f}h")
    col_c.metric("Ratio Morning/Evening", f"{ratio:.2f}×", delta=dominant, delta_color="inverse" if ratio > 1 else "normal")

    if ratio > 1:
        st.error(f"❌ **Hypothesis REJECTED:** Morning listening is actually {ratio:.2f}× HIGHER than evening listening")
        # st.markdown("**Interpretation:** This suggests background listening during work/study hours dominates over leisure listening.")
    else:
        st.success(f"✅ **Hypothesis CONFIRMED:** Evening listening is {1/ratio:.2f}× higher than morning listening")



def show_hypothesis_platform(df_to_use, use_filtered_data):
    """Display visualization for Hypothesis 3 (Platform Comparison): 
    Desktop sessions are longer than mobile sessions"""

    st.subheader("Platform Comparison: Session Duration")
    st.markdown("**Assumption:** *Desktop listening sessions are longer on average than mobile sessions*")

    # ── ROBUSTNESS GUARDS ───────────────────────────────────────────────────────
    available_platforms = df_to_use['platform_type'].unique()
    if 'Mobile' not in available_platforms or 'Desktop' not in available_platforms:
        st.warning(
            "⚠️ This hypothesis requires both Mobile and Desktop data. "
            f"Only the following platform types were found: {list(available_platforms)}. "
            "Cannot run the test."
        )
        return

    # Track play durations per platform (individual plays)
    mobile_data  = df_to_use[df_to_use['platform_type'] == 'Mobile']['minutes_played']
    desktop_data = df_to_use[df_to_use['platform_type'] == 'Desktop']['minutes_played']

    # Session statistics
    SESSION_GAP = 15  # minutes

    def calculate_sessions(df, platform_type):
        """Calculate listening session durations for a specific platform type"""
        platform_df = df[df['platform_type'] == platform_type].copy().sort_values('timestamp')
        platform_df['time_gap'] = platform_df['timestamp'].diff().dt.total_seconds() / 60
        platform_df['session_id'] = (platform_df['time_gap'] > SESSION_GAP).cumsum()
        session_durations = platform_df.groupby('session_id')['minutes_played'].sum()
        return session_durations

    mobile_sessions  = calculate_sessions(df_to_use, 'Mobile')
    desktop_sessions = calculate_sessions(df_to_use, 'Desktop')

    MIN_SESSIONS = 30
    if len(mobile_sessions) < MIN_SESSIONS or len(desktop_sessions) < MIN_SESSIONS:
        st.warning(
            f"⚠️ Not enough sessions to run a reliable statistical test (minimum {MIN_SESSIONS} required). "
            f"Found {len(mobile_sessions)} mobile sessions and {len(desktop_sessions)} desktop sessions."
        )
        return


    # ── HELPERS ─────────────────────────────────────────────────────────────────
    def classify_effect(r):
        abs_r = abs(r)
        if abs_r < 0.1:   return "Negligible"
        elif abs_r < 0.3: return "Small"
        elif abs_r < 0.5: return "Medium"
        else:             return "Large"

    def compute_mwu(series_a, series_b, alternative='less'):
        """Run Mann-Whitney U and return a plain dict of results."""
        n_a, n_b = len(series_a), len(series_b)
        u_stat, p_value = stats.mannwhitneyu(series_a, series_b, alternative=alternative)
        r_effect     = 1 - (2 * u_stat) / (n_a * n_b)
        effect_label = classify_effect(r_effect)
        ratio        = series_a.median() / series_b.median()
        return dict(u_stat=u_stat, p_value=p_value, r_effect=r_effect,
                    effect_label=effect_label, ratio=ratio, n_a=n_a, n_b=n_b)

    # ── BOXPLOT ──────────────────────────────────────────────────────────────────
    st.caption(f"A session is a continuous listening block with gaps < {SESSION_GAP} min between plays")

    median_mobile_sessions  = mobile_sessions.median()
    median_desktop_sessions = desktop_sessions.median()

    p95_sess = max(mobile_sessions.quantile(0.95), desktop_sessions.quantile(0.95))
    mobile_sessions_plot  = mobile_sessions[mobile_sessions   <= p95_sess]
    desktop_sessions_plot = desktop_sessions[desktop_sessions <= p95_sess]

    fig = go.Figure()

    fig.add_trace(go.Box(
        x=mobile_sessions_plot,
        name='Mobile',
        marker_color='#1DB954',
        boxmean=False,
        hovertemplate='📱 Mobile: %{x:.1f} min<extra></extra>',
        hoveron='points',
        orientation='h'
    ))

    fig.add_trace(go.Box(
        x=desktop_sessions_plot,
        name='Desktop',
        marker_color='#1ED760',
        boxmean=False,
        hovertemplate='💻 Desktop: %{x:.1f} min<extra></extra>',
        hoveron='points',
        orientation='h'
    ))

    fig.add_annotation(
        x=median_mobile_sessions, y=0,
        text=f'Median: {median_mobile_sessions:.2f} min',
        showarrow=False, xshift=90,
        bgcolor='rgba(29, 185, 84, 0.9)',
        font=dict(color='white', size=10),
        bordercolor='black', borderwidth=1
    )
    fig.add_annotation(
        x=median_desktop_sessions, y=1,
        text=f'Median: {median_desktop_sessions:.2f} min',
        showarrow=False, xshift=90,
        bgcolor='rgba(30, 215, 96, 0.9)',
        font=dict(color='white', size=10),
        bordercolor='black', borderwidth=1
    )

    fig.update_layout(
        title='Distribution of Session Durations',
        xaxis_title='Session Duration (minutes)',
        height=450,
        template='plotly_white',
        showlegend=False,
        xaxis=dict(gridcolor='lightgray')
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("⚠️ Outliers above the 95th percentile are hidden from the chart (for readability) but included in the statistical test.")


    # ── UNIFIED SUMMARY TABLE ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Results Summary")

    # platform_stats = df_to_use.groupby('platform_type')['minutes_played'].sum() / 60
    # results_unified = pd.DataFrame({
    #     "Platform":        ["📱 Mobile", "💻 Desktop"],
    #     "Total Time":      [f"{platform_stats.get('Mobile',  0):.1f}h",
    #                         f"{platform_stats.get('Desktop', 0):.1f}h"],
    #     "Share":           [f"{platform_stats.get('Mobile',  0) / platform_stats.sum() * 100:.1f}%",
    #                         f"{platform_stats.get('Desktop', 0) / platform_stats.sum() * 100:.1f}%"],
    #     "Median Duration": [f"{median_mobile_sessions:.1f} min", f"{median_desktop_sessions:.1f} min"],
    # })
    # st.dataframe(results_unified, hide_index=True, use_container_width=True)

    total_sessions  = len(mobile_sessions) + len(desktop_sessions)
    mobile_sess_share  = len(mobile_sessions)  / total_sessions * 100
    desktop_sess_share = len(desktop_sessions) / total_sessions * 100

    col_a, col_b = st.columns(2)
    col_a.metric("📱 Mobile Median",   f"{median_mobile_sessions:.1f} min")
    col_b.metric("💻 Desktop Median",  f"{median_desktop_sessions:.1f} min")

    col_c, col_d = st.columns(2)
    col_c.metric("📱 Number of Mobile Sessions",  f"{len(mobile_sessions):,}",  delta=f"{mobile_sess_share:.1f}% of sessions", delta_arrow="off", delta_color="off")
    col_d.metric("💻 Number of Desktop Sessions", f"{len(desktop_sessions):,}", delta=f"{desktop_sess_share:.1f}% of sessions", delta_arrow="off", delta_color="off")


    # ── VERDICT ─────────────────────────────────────────────────────────────────
    mwu = compute_mwu(mobile_sessions, desktop_sessions, alternative='less')

    if mwu['p_value'] >= 0.05:
        st.warning(
            f"⚠️ **Inconclusive** — No statistically significant difference between platforms "
            f"(p = {mwu['p_value']:.4f} ≥ 0.05, effect: {mwu['effect_label']})"
        )
    elif mwu['ratio'] < 1:
        st.success(
            f"✅ **Hypothesis CONFIRMED** — Desktop sessions are statistically longer than mobile sessions "
            f"(p = {mwu['p_value']:.4f}, effect: {mwu['effect_label']})"
        )
    else:
        st.error(
            f"❌ **Hypothesis REJECTED** — Mobile sessions are actually longer than desktop sessions "
            f"(p = {mwu['p_value']:.4f}, effect: {mwu['effect_label']})"
        )



    # ── STATISTICAL DETAILS (EXPANDER) ───────────────────────────────────────────
    with st.expander("Statistical test details (Mann-Whitney U test)"):
        st.caption("Null Hypothesis (H₀): mobile session durations ≥ desktop session durations")
        st.caption("Alternative Hypothesis (H₁): mobile session durations < desktop session durations")

        st.markdown(
            "The **Mann-Whitney U test** is a non-parametric test that checks whether values "
            "from one group tend to be larger than those from another, without assuming a normal distribution. "
            "A **p-value < 0.05** indicates a statistically significant difference. "
            "**Effect size r** (rank-biserial correlation) measures practical magnitude: "
            "< 0.1 = Negligible, < 0.3 = Small, < 0.5 = Medium, ≥ 0.5 = Large."
        )
        test_results = pd.DataFrame({
            "Test":              ["Mann-Whitney U"],
            "U-statistic":       [f"{mwu['u_stat']:.0f}"],
            "p-value":           [f"{mwu['p_value']:.4f}"],
            "Effect Size r":     [f"{mwu['r_effect']:.3f}"],
            "Effect Size Label": [mwu['effect_label']],
            "n Mobile":          [mwu['n_a']],
            "n Desktop":         [mwu['n_b']],
        })
        st.dataframe(test_results, hide_index=True, use_container_width=True)



### MAIN APP ###

def show_main_app(username):
    """
    Display main application interface with data upload and all analysis sections.
    Data is stored in st.session_state so it persists across page navigation.
    """

    # Sidebar navigation — always visible regardless of whether data is loaded
    st.sidebar.header("Navigation")
    st.sidebar.radio(
        "Go to",
        ["App Overview", "Valid Streams Filtering", "Top Content", "Temporal Analysis", "Hypothesis Testing"],
        key="current_page"
    )

    page = st.session_state["current_page"]

    # ── APP OVERVIEW ────────────────────────────────────────────────────────────
    if page == "App Overview":
        st.markdown("<h1 style='color: #1DB954;'>🎧 Listening Data Explorer</h1>", unsafe_allow_html=True)
        st.caption("Exploratory analysis of personal music listening behavior on Spotify")
        st.markdown("---")

        # Mode selection: Demo vs Upload
        st.subheader("Choose Data Source")
        
        mode = st.radio(
            "Select mode:",
            ["Try demo mode", "Or upload your own data"],
            index=None,
            help="Demo mode uses pre-processed data from the author's. Upload mode allows you to analyze your own Spotify history.",
            horizontal=True,
        )
                
        # ── DEMO MODE ───────────────────────────────────────────────────────────
        if mode == "Try demo mode":
            # st.info("🎭 **Demo Mode** — You will be viewing the author's listening data from 2025.")
            st.markdown("---")
            st.subheader("🎭 Demo Mode")
            st.markdown("You will be viewing the author's listening data from 2025. This allows you to explore the app's features without uploading your own data.")

            # Load demo data button
            if st.button("📊 Load Demo Data", type="primary"):
                try:
                    with st.spinner("Loading demo data..."):
                        df, df_valid = load_demo_data()
                        st.session_state["df"] = df
                        st.session_state["df_valid"] = df_valid
                        st.session_state["demo_mode"] = True
                except Exception as e:
                    st.error(f"Error loading demo data: {str(e)}")
                    st.info("Make sure the `demo_data/` folder exists with the parquet files.")
            
            # If data already loaded in session, show it
            if "df" in st.session_state and st.session_state.get("demo_mode", False):
                df = st.session_state["df"]
                df_valid = st.session_state["df_valid"]
                st.success(f"✅ Demo data loaded! {len(df):,} total plays, from {df['date'].min()} to {df['date'].max()}")
                st.markdown("---")
                show_overview(df, df_valid)


        # ── UPLOAD MODE ─────────────────────────────────────────────────────────
        elif mode == "Or upload your own data":
            st.markdown("---")
            st.subheader("📁 Upload Your Own Spotify Data")
            st.markdown("Upload your *Extended Streaming History* JSON files exported from Spotify."
                        " Files are typically named `Streaming_History_Audio_*.json`."
                        " You can select multiple files at once.")
            uploaded_files = st.file_uploader("",
                type=['json'],
                accept_multiple_files=True,
                key="uploaded_files"
            )

            # Process newly uploaded files and persist in session_state
            if uploaded_files:
                try:
                    with st.spinner("Processing data..."):
                        df, df_valid = load_and_process_user_data(uploaded_files)
                        st.session_state["df"] = df
                        st.session_state["df_valid"] = df_valid
                        st.session_state["demo_mode"] = False
                except Exception as e:
                    st.error(f"Error processing data: {str(e)}")
                    st.info("Please make sure you've uploaded valid Spotify Extended Streaming History JSON files.")

            # Retrieve data from session_state (covers both fresh upload and returning to this page)
            if "df" in st.session_state and not st.session_state.get("demo_mode", False):
                df = st.session_state["df"]
                df_valid = st.session_state["df_valid"]
                st.success(f"✅ Data loaded! {len(df):,} total plays, from {df['date'].min()} to {df['date'].max()}")
                st.markdown("---")
                show_overview(df, df_valid)
            else:
                # No data uploaded yet — show how-to instructions
                with st.expander("ℹ️ How to get your Spotify data"):
                    st.markdown("""
                    1. Go to [Spotify Account Privacy Settings](https://www.spotify.com/account/privacy/)
                    2. Request your **Extended Streaming History**
                    3. Wait for the email (between 1-30 days)
                    4. Download and extract the zip files
                    5. Upload the JSON files above (named `Streaming_History_Audio_*.json`)
                    """)
        
        else:
            st.warning("Please select a mode to proceed.")
        

        st.markdown("---")
        st.subheader("📋 About This App")
        st.markdown("""
        This app analyses your personal Spotify listening history across 5 sections:

        | Section | Description |
        |---|---|
        | **App Overview** | Upload your data and view top-level statistics |
        | **Valid Streams Filtering** | Understand the 30-second threshold used by Spotify |
        | **Top Content** | Your top artists, tracks and albums |
        | **Temporal Analysis** | How your listening habits vary by hour, day and over time |
        | **Hypothesis Testing** | Three data-driven hypotheses about your listening behaviour |
        """)


    # ── ALL OTHER PAGES ─────────────────────────────────────────────────────────
    else:
        # Guard: data must be loaded first
        if "df" not in st.session_state:
            st.warning("⚠️ Please select the demo mode or upload your Spotify data in the **App Overview** section first.")
            return

        df = st.session_state["df"]
        df_valid = st.session_state["df_valid"]

        if page == "Valid Streams Filtering":
            show_valid_streams_filtering(df, df_valid)

        elif page == "Top Content":
            show_top_content(df, df_valid)

        elif page == "Temporal Analysis":
            show_temporal_analysis(df, df_valid)

        elif page == "Hypothesis Testing":
            st.header("Hypothesis Testing")
            st.markdown("""
            This section tests few naive assumptions about listening behavior.
            """)

            # Global filter for all sub-tabs
            use_filtered_data = st.checkbox(
                "Apply 30-second filter (recommended)",
                value=True,
                key="filter_hypothesis",
                help="Only include streams ≥30 seconds for all hypothesis tests"
            )

            df_to_use = df_valid if use_filtered_data else df

            if use_filtered_data:
                st.caption(f"All analyses below use valid streams only (≥30s) — {len(df_valid):,} plays")
            else:
                st.caption(f"All analyses below use all plays (including <30s) — {len(df):,} plays")

            # st.markdown("---")

            tab1, tab2, tab3 = st.tabs([
                "📈 Pareto Principle",
                "💻 Platform Comparison",
                "🕐 Time of Day"
            ])

            with tab1:
                show_hypothesis_pareto(df_to_use, use_filtered_data)

            with tab2:
                show_hypothesis_platform(df_to_use, use_filtered_data)

            with tab3:
                show_hypothesis_time_of_day(df_to_use, use_filtered_data)




### MAIN

def main():
    """Run the Streamlit application without authentication"""

    # init_db()
    
    # # Sidebar user menu
    # with st.sidebar:
    #     st.header("👤 User")Justé, c'est la plupart de ces différentes choses. Merci pour l'identification.

    #     if st.session_state.get("logged_in", False):
    #         st.write(f"🟢 {st.session_state['username']}")
    #         if st.button("Logout"):
    #             log_action(st.session_state["username"], "logout")
    #             st.session_state["logged_in"] = False
    #             st.session_state["username"] = None
    #             st.rerun()
    #     else:
    #         st.write("Not logged in")
    
    # # Show login or main app
    # if not st.session_state.get("logged_in", False):
    #     show_login_page()
    # else:
    #     show_main_app(st.session_state["username"])
    
    # Direct access without login
    show_main_app(username=None)

if __name__ == "__main__":
    main()
