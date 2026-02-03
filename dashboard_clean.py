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

# ===== HEADER =====
st.markdown("""
<div class="title-container">
    <h1 class="main-title">Counseling Bot Analytics Dashboard</h1>
</div>
""", unsafe_allow_html=True)

# ===== LOAD DATA =====
@st.cache_data(ttl=300)
def load_data(api_key, days, project_name):
    """Load conversation data from LangSmith API"""
    conversations = get_langsmith_data(api_key, days, project_name)
    
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

# Load data
try:
    # Default to 300 days to get all available data
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
    
    with col1:
        st.markdown("**📅 Date Range**")
        date_range = st.date_input(
            "dates",
            value=(df['date'].min(), df['date'].max()),
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("**👤 Users**")
        all_users = ['All'] + sorted(df['user_name'].dropna().unique().tolist())
        selected_users = st.multiselect("users", all_users, default=['All'], label_visibility="collapsed")
    
    with col3:
        st.markdown("**✅ Status**")
        success_options = ['All', 'Successful', 'Failed']
        success_filter = st.selectbox("status", success_options, label_visibility="collapsed")
    
    with col4:
        st.markdown("**�**")
        if st.button("Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col5:
        st.write("")
    
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
    
    # ===== KEY METRICS =====
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_conversations = len(filtered_df)
    successful_conversations = int(filtered_df['success'].sum())
    success_rate = (successful_conversations / total_conversations * 100) if total_conversations > 0 else 0
    avg_response_time = filtered_df['latency_seconds'].mean()
    unique_users = filtered_df['user_name'].nunique()
    
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
    
    # ===== SECTION 1: Conversations Over Time =====
    st.markdown("---")
    st.header("📈 Conversations Over Time")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        time_agg = st.radio("View By", ["Daily", "Weekly", "Monthly"], horizontal=True)
    
    with col1:
        if time_agg == "Daily":
            time_series = filtered_df.groupby(filtered_df['date'].dt.date).agg({
                'conversation_id': 'count',
                'success': lambda x: (x.sum() / len(x) * 100)
            }).reset_index()
            time_series.columns = ['date', 'conversations', 'success_rate']
        elif time_agg == "Weekly":
            time_series = filtered_df.groupby([filtered_df['timestamp'].dt.isocalendar().year, 
                                               filtered_df['timestamp'].dt.isocalendar().week]).agg({
                'conversation_id': 'count',
                'success': lambda x: (x.sum() / len(x) * 100)
            }).reset_index()
            time_series.columns = ['year', 'week', 'conversations', 'success_rate']
            time_series['date'] = time_series['year'].astype(str) + '-W' + time_series['week'].astype(str)
        else:  # Monthly
            time_series = filtered_df.groupby(filtered_df['timestamp'].dt.to_period('M')).agg({
                'conversation_id': 'count',
                'success': lambda x: (x.sum() / len(x) * 100)
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
    
    # ===== SECTION 2: Response Time Analysis =====
    st.markdown("---")
    st.header("⚡ Response Time Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Response Time Distribution")
        fig = px.histogram(
            filtered_df,
            x='latency_seconds',
            nbins=30,
            labels={'latency_seconds': 'Response Time (seconds)'},
            color_discrete_sequence=['#667eea']
        )
        fig.update_layout(template='plotly_white', height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Response Time Over Time")
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
    
    # ===== SECTION 3: Most Active Users =====
    st.markdown("---")
    st.header("👥 Most Active Users")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        top_users = filtered_df.groupby('user_name').agg({
            'conversation_id': 'count',
            'success': lambda x: (x.sum() / len(x) * 100),
            'latency_seconds': 'mean'
        }).reset_index()
        top_users.columns = ['user_name', 'conversations', 'success_rate', 'avg_response_time']
        top_users = top_users.sort_values('conversations', ascending=False).head(10)
        
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
    
    with col2:
        st.subheader("User Statistics")
        for _, user in top_users.head(5).iterrows():
            with st.expander(f"👤 {user['user_name']}"):
                st.metric("Conversations", f"{int(user['conversations'])}")
                st.metric("Success Rate", f"{user['success_rate']:.1f}%")
                st.metric("Avg Response", f"{user['avg_response_time']:.1f}s")
    
    # ===== SECTION 4: Usage Patterns =====
    st.markdown("---")
    st.header("⏰ Usage Patterns")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("By Day of Week")
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
    
    with col2:
        st.subheader("By Hour of Day")
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
    
    # ===== SECTION 5: Recent Activity =====
    st.markdown("---")
    st.header("💬 Recent Conversations")
    
    recent = filtered_df.nlargest(20, 'timestamp')[
        ['timestamp', 'user_name', 'run_name', 'latency_seconds', 'success', 'status']
    ].copy()
    
    recent['Time'] = recent['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    recent['Success'] = recent['success'].apply(lambda x: '✅' if x else '❌')
    recent['Response Time'] = recent['latency_seconds'].apply(lambda x: f"{x:.2f}s")
    
    display_df = recent[['Time', 'user_name', 'run_name', 'Response Time', 'Success', 'status']]
    display_df.columns = ['Timestamp', 'User', 'Bot Type', 'Response Time', 'Success', 'Status']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
    
    # ===== FOOTER =====
    st.markdown("---")
    st.caption(f"""
        📊 Dashboard showing {len(filtered_df):,} conversations from {unique_users:,} users | 
        Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)

except Exception as e:
    st.error(f"❌ Error loading dashboard: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
