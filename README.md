# LangSmith Analytics Dashboard

A simple, standalone analytics dashboard for monitoring LangSmith tracing data using Streamlit and Plotly.

## Features

✨ **Real-time Monitoring**
- Live statistics (total runs, success rate, latency, token usage, costs)
- Auto-refresh capability
- Customizable time ranges (1-30 days)

📊 **Interactive Charts** (Plotly)
- Activity over time
- Latency trends
- Token usage visualization
- Cost tracking

🔍 **Misuse Detection**
- Suspicious usage pattern detection
- High-frequency request alerts
- Excessive token usage warnings
- Error rate monitoring

📈 **Error Analysis**
- Error categorization
- Error distribution charts
- Recent error examples

## Installation

1. Navigate to the dashboard directory:
```bash
cd dashboard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your LangSmith API key
```

Required environment variables:
- `LANGCHAIN_API_KEY`: Your LangSmith API key
- `LANGCHAIN_PROJECT`: Your LangSmith project name

## Usage

### Start the Dashboard

Simply run:

```bash
streamlit run dashboard.py
```

The dashboard will open automatically in your browser at **http://localhost:8501**

### Using the Dashboard

1. **Select Time Range**: Choose from 1-30 days in the sidebar
2. **Enter Project Name**: Filter by specific project (optional)
3. **Refresh**: Click the refresh button to update data
4. **Auto-Refresh**: Enable automatic updates every 60 seconds

### Misuse Detection

The dashboard automatically detects suspicious patterns:

- 🚨 **High Frequency**: >100 requests/hour
- 🚨 **Excessive Tokens**: >8000 avg tokens/request
- 🚨 **High Error Rate**: >50% errors

Suspicious activity is highlighted with warnings.

## File Structure

```
dashboard/
├── dashboard.py          # Main Streamlit app
├── data_fetcher.py       # LangSmith data retrieval
├── requirements.txt
├── .env.example
└── README.md
```

Simple and clean - just 2 Python files!

## Customization

### Modify Cost Calculation

Edit `data_fetcher.py` and update the `calculate_cost()` function:

```python
costs = {
    "your-model": 0.XX,  # Cost per 1K tokens
}
```

### Adjust Misuse Thresholds

Edit the misuse detection section in `dashboard.py`:

```python
hourly['suspicious'] = (
    (hourly['run_count'] > 100) |  # Change threshold
    (hourly['avg_tokens'] > 8000) |
    (hourly['error_rate'] > 50)
)
```

## Troubleshooting

**Issue**: "No module named 'langsmith'"
- **Solution**: Run `pip install -r requirements.txt`

**Issue**: No data displayed
- **Solution**: Check `.env` file has correct `LANGCHAIN_API_KEY` and `LANGCHAIN_PROJECT`

**Issue**: Charts not rendering
- **Solution**: Make sure Plotly is installed: `pip install plotly`

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The `.env` file is already in `.gitignore`
- For production, use Streamlit Cloud's secrets management

## License

This dashboard is part of the counselling-bot project.
