import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_fetcher import get_langsmith_data

# Configuration - Use Streamlit secrets
API_KEY = st.secrets["LANGSMITH_API_KEY"]
PROJECT_NAME = st.secrets.get("PROJECT_NAME")

# Page config
st.set_page_config(
    page_title="Counseling Bot Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {background-color: #f8f9fa;}
    
    .title-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        color: white;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        color: white;
    }
    
    .filter-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #6c757d;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ===== HELPER FUNCTIONS =====
def has_real_name(username):
    """Check if username appears to be a real name (not UUID or system-generated)"""
    if pd.isna(username) or username == 'Unknown' or username == '':
        return False
    
    username_str = str(username).strip()
    
    # Check for system-generated patterns like "User-abc123" or "Guest-abc123"
    if username_str.startswith(('User-', 'Guest-', 'user-', 'guest-')):
        return False
    
    # Check if it looks like a UUID (contains many hyphens and hex characters)
    if len(username_str) > 20 and username_str.count('-') >= 3:
        return False
    
    # Check if it's all hex characters (with or without hyphens)
    cleaned = username_str.replace('-', '').replace('_', '')
    if len(cleaned) > 16 and all(c in '0123456789abcdefABCDEF' for c in cleaned):
        return False
    
    return True

# ===== LOAD DATA =====
@st.cache_data(ttl=300)
def load_data(api_key, days, project_name, force_refresh=False):
    """Load conversation data from LangSmith API"""
    conversations = get_langsmith_data(api_key, days, project_name, force_full_refresh=force_refresh)
    
    if not conversations:
        st.error("No conversations found!")
        st.stop()
    
    # Convert to DataFrame
    df = pd.DataFrame(conversations)
    
    # Convert timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = pd.to_datetime(df['timestamp'].dt.date)
    
    # Use user_name from the data (which comes from run.name or generated)
    # The data_fetcher should be updated to extract proper usernames
    if 'user_name' not in df.columns:
        df['user_name'] = df.get('user_id', 'Unknown')
    
    # Ensure success is boolean
    df['success'] = df['success'].astype(bool)
    
    # Convert latency from ms to seconds
    df['latency_seconds'] = df['latency_ms'] / 1000 if 'latency_ms' in df.columns else 0
    
    # Add status field
    df['status'] = df['success'].apply(lambda x: '✅ Success' if x else '❌ Failed')
    
    return df

# ===== HEADER WITH REFRESH BUTTON =====
col_title, col_refresh = st.columns([5, 1])

with col_title:
    st.markdown("""
    <div class="title-container">
        <h1 class="main-title">Counseling Bot Analytics Dashboard</h1>
    </div>
    """, unsafe_allow_html=True)

with col_refresh:
    st.write("")  # Spacing
    if st.button("🔄 Force Refresh", help="Clear cache and fetch all data from scratch"):
        st.cache_data.clear()
        st.rerun()

# Load data
try:
    # Default to 355 days to get all available data on first run
    days_to_load = 355
    
    with st.spinner("Loading conversation data from LangSmith..."):
        df = load_data(API_KEY, days_to_load, PROJECT_NAME)
    
    if len(df) == 0:
        st.warning("No conversations found in the data.")
        st.stop()
    
    # Add computed fields
    df['month'] = df['timestamp'].dt.to_period('M').astype(str)
    df['week'] = df['timestamp'].dt.isocalendar().week
    df['month_name'] = df['timestamp'].dt.strftime('%B')
    df['year'] = df['timestamp'].dt.year
    df['day_of_week'] = df['timestamp'].dt.day_name()
    df['hour'] = df['timestamp'].dt.hour
    
    # ===== HORIZONTAL FILTERS =====
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.subheader("🔍 Filters")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Define default date range: September 1, 2025 to today
    default_start_date = datetime(2025, 9, 1).date()
    default_end_date = datetime.now().date()
    
    # Initialize session state for date range if not exists
    if 'date_range_start' not in st.session_state:
        st.session_state.date_range_start = default_start_date
    if 'date_range_end' not in st.session_state:
        st.session_state.date_range_end = default_end_date
    
    with col1:
        st.markdown("**📅 Date Range**")
        date_range = st.date_input(
            "dates",
            value=(st.session_state.date_range_start, st.session_state.date_range_end),
            label_visibility="collapsed",
            key="date_input"
        )
        # Update session state when user changes dates
        if isinstance(date_range, tuple) and len(date_range) == 2:
            st.session_state.date_range_start = date_range[0]
            st.session_state.date_range_end = date_range[1]
    
    with col2:
        st.markdown("**👤 Users**")
        # Filter to only show users with real names (not generated usernames)
        real_usernames = [user for user in df['user_name'].dropna().unique() if has_real_name(user)]
        all_users = ['All'] + sorted(real_usernames)
        selected_users = st.multiselect("users", all_users, default=['All'], label_visibility="collapsed")
    
    with col3:
        st.markdown("**✅ Status**")
        success_options = ['All', 'Successful', 'Failed']
        success_filter = st.selectbox("status", success_options, label_visibility="collapsed")
    
    with col4:
        st.markdown("**🔄 Refresh**")
        if st.button("Refresh Data", use_container_width=True, help="Refresh dashboard with latest data"):
            st.cache_data.clear()
            st.rerun()
    
    with col5:
        st.markdown("**🔁 Reset**")
        if st.button("Reset Date", use_container_width=True, help="Reset date range to Sept 1 - Today"):
            st.session_state.date_range_start = default_start_date
            st.session_state.date_range_end = default_end_date
            st.cache_data.clear()
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Apply filters
    filtered_df = df.copy()
    
    # Date filter
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]
    
    if success_filter == 'Successful':
        filtered_df = filtered_df[filtered_df['success'] == True]
    elif success_filter == 'Failed':
        filtered_df = filtered_df[filtered_df['success'] == False]
    
    if 'All' not in selected_users:
        filtered_df = filtered_df[filtered_df['user_name'].isin(selected_users)]
    
    # Check if filtered data is empty
    if len(filtered_df) == 0:
        st.warning("⚠️ No data matches the selected filters. Please adjust your filter criteria.")
        st.stop()
    
    # ===== KEY METRICS =====
    st.markdown("---")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    try:
        total_conversations = len(filtered_df)
        successful_conversations = int(filtered_df['success'].sum())
        success_rate = (successful_conversations / total_conversations * 100) if total_conversations > 0 else 0
        avg_response_time = filtered_df['latency_seconds'].mean() if 'latency_seconds' in filtered_df.columns else 0
        unique_users = filtered_df['user_name'].nunique() if 'user_name' in filtered_df.columns else 0
        slow_traces = len(filtered_df[filtered_df['latency_seconds'] > 15]) if 'latency_seconds' in filtered_df.columns else 0
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        total_conversations = successful_conversations = success_rate = avg_response_time = unique_users = slow_traces = 0
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_conversations:,}</div>
            <div class="metric-label">Total Conversations</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{success_rate:.1f}%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_response_time:.1f}s</div>
            <div class="metric-label">Avg Response Time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{unique_users:,}</div>
            <div class="metric-label">Unique Users</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{slow_traces:,}</div>
            <div class="metric-label">Slow Traces (>15s)</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ===== SECTION 1: Conversations Over Time =====
    st.markdown("---")
    st.header("📈 Conversations Over Time")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        time_agg = st.radio("View By", ["Daily", "Weekly", "Monthly"], horizontal=True)
    
    with col1:
        try:
            if time_agg == "Daily":
                time_series = filtered_df.groupby(filtered_df['date'].dt.date).agg({
                    'conversation_id': 'count',
                    'success': lambda x: (x.sum() / len(x) * 100) if len(x) > 0 else 0
                }).reset_index()
                time_series.columns = ['date', 'conversations', 'success_rate']
            elif time_agg == "Weekly":
                time_series = filtered_df.groupby([filtered_df['timestamp'].dt.isocalendar().year, 
                                                   filtered_df['timestamp'].dt.isocalendar().week]).agg({
                    'conversation_id': 'count',
                    'success': lambda x: (x.sum() / len(x) * 100) if len(x) > 0 else 0
                }).reset_index()
                time_series.columns = ['year', 'week', 'conversations', 'success_rate']
                time_series['date'] = time_series['year'].astype(str) + '-W' + time_series['week'].astype(str)
            else:  # Monthly
                time_series = filtered_df.groupby(filtered_df['timestamp'].dt.to_period('M')).agg({
                    'conversation_id': 'count',
                    'success': lambda x: (x.sum() / len(x) * 100) if len(x) > 0 else 0
                }).reset_index()
                time_series.columns = ['date', 'conversations', 'success_rate']
                time_series['date'] = time_series['date'].astype(str)
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(
                go.Bar(
                    x=time_series['date'],
                    y=time_series['conversations'],
                    name="Conversations",
                    marker_color='#667eea'
                ),
                secondary_y=False,
            )
            
            fig.add_trace(
                go.Scatter(
                    x=time_series['date'],
                    y=time_series['success_rate'],
                    name="Success Rate (%)",
                    line=dict(color='#10b981', width=3),
                    mode='lines+markers'
                ),
                secondary_y=True,
            )
            
            fig.update_xaxes(title_text="Date")
            fig.update_yaxes(title_text="Number of Conversations", secondary_y=False)
            fig.update_yaxes(title_text="Success Rate (%)", secondary_y=True)
            
            fig.update_layout(
                template='plotly_white',
                height=400,
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error creating time series chart: {str(e)}")
    
    # ===== SECTION 2: Response Time Analysis =====
    st.markdown("---")
    st.header("⚡ Response Time Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Response Time Distribution")
        try:
            if 'latency_seconds' in filtered_df.columns and len(filtered_df) > 0:
                fig = px.histogram(
                    filtered_df,
                    x='latency_seconds',
                    nbins=30,
                    labels={'latency_seconds': 'Response Time (seconds)'},
                    color_discrete_sequence=['#667eea']
                )
                fig.update_layout(template='plotly_white', height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No latency data available.")
        except Exception as e:
            st.error(f"Error creating response time distribution: {str(e)}")
    
    with col2:
        st.subheader("Response Time Over Time")
        try:
            if 'latency_seconds' in filtered_df.columns and len(filtered_df) > 0:
                daily_latency = filtered_df.groupby(filtered_df['date'].dt.date)['latency_seconds'].mean().reset_index()
                daily_latency.columns = ['date', 'avg_latency']
                
                fig = px.line(
                    daily_latency,
                    x='date',
                    y='avg_latency',
                    labels={'avg_latency': 'Avg Response Time (s)', 'date': 'Date'},
                    markers=True
                )
                fig.update_traces(line_color='#f59e0b', line_width=3)
                fig.update_layout(template='plotly_white', height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No latency data available.")
        except Exception as e:
            st.error(f"Error creating response time chart: {str(e)}")
    
    # ===== SECTION 3: Most Active Users =====
    st.markdown("---")
    st.header("👥 Most Active Users")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Filter to only users with real names
        real_users_df = filtered_df[filtered_df['user_name'].apply(has_real_name)]
        
        # Check if there are any users with real names
        if len(real_users_df) == 0 or 'user_name' not in real_users_df.columns:
            st.info("No users with real names found in the filtered data.")
            top_users = pd.DataFrame(columns=['user_name', 'conversations', 'success_rate', 'avg_response_time'])
        else:
            top_users = real_users_df.groupby('user_name').agg({
                'conversation_id': 'count',
                'success': lambda x: (x.sum() / len(x) * 100),
                'latency_seconds': 'mean'
            }).reset_index()
            top_users.columns = ['user_name', 'conversations', 'success_rate', 'avg_response_time']
            top_users = top_users.sort_values('conversations', ascending=False).head(10)
        
        if len(top_users) > 0:
            fig = px.bar(
                top_users,
                y='user_name',
                x='conversations',
                orientation='h',
                labels={'user_name': 'User', 'conversations': 'Number of Conversations'},
                color='conversations',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(template='plotly_white', height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No user data available to display.")
    
    with col2:
        st.subheader("User Statistics")
        try:
            if len(top_users) > 0:
                for _, user in top_users.head(5).iterrows():
                    with st.expander(f"👤 {user['user_name']}"):
                        st.metric("Conversations", f"{int(user['conversations'])}")
                        st.metric("Success Rate", f"{user['success_rate']:.1f}%")
                        st.metric("Avg Response", f"{user['avg_response_time']:.1f}s")
            else:
                st.info("No user statistics available.")
        except Exception as e:
            st.error(f"Error displaying user statistics: {str(e)}")
    
    # ===== SECTION 4: Usage Patterns =====
    st.markdown("---")
    st.header("⏰ Usage Patterns")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("By Day of Week")
        try:
            if 'day_of_week' in filtered_df.columns and len(filtered_df) > 0:
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_counts = filtered_df['day_of_week'].value_counts().reindex(day_order).reset_index()
                day_counts.columns = ['day', 'count']
                
                fig = px.bar(
                    day_counts,
                    x='day',
                    y='count',
                    labels={'day': 'Day of Week', 'count': 'Conversations'},
                    color='count',
                    color_continuous_scale='Blues'
                )
                fig.update_layout(template='plotly_white', height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No day of week data available.")
        except Exception as e:
            st.error(f"Error creating day of week chart: {str(e)}")
    
    with col2:
        st.subheader("By Hour of Day")
        try:
            if 'hour' in filtered_df.columns and len(filtered_df) > 0:
                hourly = filtered_df.groupby('hour').size().reset_index(name='count')
                
                fig = px.line(
                    hourly,
                    x='hour',
                    y='count',
                    labels={'hour': 'Hour of Day', 'count': 'Conversations'},
                    markers=True
                )
                fig.update_traces(line_color='#ef4444', marker_size=10, line_width=3)
                fig.update_layout(template='plotly_white', height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hourly data available.")
        except Exception as e:
            st.error(f"Error creating hourly chart: {str(e)}")
    
    # ===== SECTION 5: Recent Activity =====
    st.markdown("---")
    st.header("💬 Recent Conversations")
    
    try:
        # Filter to only users with real names
        real_users_df = filtered_df[filtered_df['user_name'].apply(has_real_name)]
        
        if len(real_users_df) > 0:
            recent = real_users_df.nlargest(30, 'timestamp')[
                ['timestamp', 'user_name', 'run_name', 'latency_seconds', 'success', 'status']
            ].copy()
            
            recent['Time'] = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            recent['Success'] = recent['success'].apply(lambda x: '✅' if x else '❌')
            recent['Response Time'] = recent['latency_seconds'].apply(lambda x: f"{x:.2f}s" if pd.notna(x) else 'N/A')
            
            display_df = recent[['Time', 'user_name', 'run_name', 'Response Time', 'Success', 'status']]
            display_df.columns = ['Timestamp', 'User', 'Bot Type', 'Response Time', 'Success', 'Status']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No recent conversations with real user names found.")
    except Exception as e:
        st.error(f"Error displaying recent conversations: {str(e)}")
    
    # ===== FOOTER =====
    st.markdown("---")
    
    try:
        # Check if cache exists
        import os
        cache_dir = os.path.join(os.path.dirname(__file__), '.cache')
        timestamp_file = os.path.join(cache_dir, 'last_fetch_timestamp.json')
        
        cache_info = ""
        if os.path.exists(timestamp_file):
            import json
            try:
                with open(timestamp_file, 'r') as f:
                    data = json.load(f)
                    last_fetch = datetime.fromisoformat(data['last_fetch'])
                    cache_info = f" | 🔄 Cache updated: {last_fetch.strftime('%Y-%m-%d %H:%M:%S')} | Next refresh: incremental"
            except:
                cache_info = " | 🔄 Using incremental updates"
        else:
            cache_info = " | 🔄 First run - building cache"
        
        st.caption(f"""
            📊 Dashboard showing {len(filtered_df):,} conversations from {unique_users:,} users | 
            Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{cache_info}
        """)
    except Exception as e:
        st.caption(f"📊 Dashboard | Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

except Exception as e:
    st.error(f"❌ Error loading dashboard: {str(e)}")
    
    with st.expander("Show detailed error information"):
        import traceback
        st.code(traceback.format_exc())
    
    st.info("💡 Try clicking the 'Force Refresh' button at the top to clear cache and reload data.")
