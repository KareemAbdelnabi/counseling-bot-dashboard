"""LangSmith data fetcher for counseling bot analytics."""

from langsmith import Client
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json




def get_langsmith_data(api_key: str, days: int = 7, project_name: str = "counseling-bot-production"):
    """
    Fetch conversation data from LangSmith traces.
    
    Returns data in format:
    {
        "conversation_id": str,
        "user_id": str,
        "timestamp": datetime,
        "conversation_steps": [steps],
        "user_profile": dict,
        "program_recommended": str,
        "success": bool,
        "total_tokens": int,
        "latency_ms": float
    }
    """
    client = Client(api_key=api_key)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    conversations = []
    
    for run in client.list_runs(
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        is_root=1
    ):
        # Extract conversation data
        conversation_id = str(run.id)
        timestamp = run.start_time
        
        # Extract user name/identifier - prefer actual name over UUID
        user_name = None
        user_id = None
        run_name = None
        
        # Try to get name from run attributes
        if hasattr(run, 'name') and run.name:
            run_name = run.name
            # Don't use run.name as user_name since it's the bot/model name
        
        # Try to get from metadata and inputs
        if hasattr(run, 'extra') and run.extra:
            user_name = run.extra.get('name') or run.extra.get('username')
            user_id = run.extra.get('user_id') or run.extra.get('session_id')
        
        # Try to get username from inputs (this is where actual user names are stored)
        if hasattr(run, 'inputs') and run.inputs:
            input_username = run.inputs.get('user_input_username') or run.inputs.get('username')
            if input_username and not user_name:
                user_name = str(input_username)
        
        # Try session_id
        if not user_id and hasattr(run, 'session_id'):
            user_id = str(run.session_id) if run.session_id else None
        
        # Fallback to generated name
        if not user_name:
            user_name = f"User-{hash(conversation_id) % 10000}"
        
        if not user_id:
            user_id = str(conversation_id)
        
        # Calculate latency
        latency_ms = None
        if run.end_time and run.start_time:
            latency_ms = (run.end_time - run.start_time).total_seconds() * 1000
        
        # Extract tokens
        total_tokens = None
        if hasattr(run, 'extra') and run.extra:
            usage = run.extra.get('usage', {})
            total_tokens = usage.get('total_tokens')
        
        # Extract input/output
        user_input = ''
        bot_response = ''
        
        if hasattr(run, 'inputs') and run.inputs:
            input_val = run.inputs.get('user_input')
            if not input_val:
                input_val = run.inputs.get('input')
            if input_val is not None:
                user_input = str(input_val) if not isinstance(input_val, str) else input_val
        
        if hasattr(run, 'outputs') and run.outputs:
            output_val = run.outputs.get('output')
            if not output_val:
                output_val = run.outputs.get('response')
            if output_val is not None:
                bot_response = str(output_val) if not isinstance(output_val, str) else output_val
        
        # Build conversation steps (simplified - single step for now)
        conversation_steps = []
        if user_input or bot_response:
            conversation_steps.append({
                'step_number': 1,
                'user_input': user_input,
                'bot_response': bot_response,
                'confidence_score': 0.95  # Default high confidence
            })
        
        # Extract user profile (mock data if not available)
        user_profile = {
            'age': None,
            'education_level': 'Unknown',
            'grades': None
        }
        
        if hasattr(run, 'extra') and run.extra:
            profile = run.extra.get('user_profile', {})
            if profile:
                user_profile.update(profile)
        
        # Extract recommended program from output
        program_recommended = None
        if bot_response and isinstance(bot_response, str):
            # Try to extract program mentions from response
            # This is a simplified extraction - adjust based on your actual data
            response_lower = bot_response.lower()
            if 'engineering' in response_lower:
                program_recommended = 'Engineering'
            elif 'business' in response_lower:
                program_recommended = 'Business'
            elif 'medicine' in response_lower:
                program_recommended = 'Medicine'
            elif 'computer science' in response_lower or 'computing' in response_lower:
                program_recommended = 'Computer Science'
            elif 'arts' in response_lower:
                program_recommended = 'Arts'
            elif 'law' in response_lower:
                program_recommended = 'Law'
            elif 'science' in response_lower:
                program_recommended = 'Science'
            else:
                program_recommended = 'General Counseling'
        else:
            program_recommended = 'General Counseling'
        
        # Determine success (ensure it's always boolean)
        is_success = bool(
            getattr(run, 'status', 'success') == 'success' and 
            not getattr(run, 'error', None) and 
            bot_response and len(str(bot_response)) > 0
        )
        
        conversation = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'user_name': user_name,
            'run_name': run_name,
            'timestamp': timestamp,
            'conversation_steps': conversation_steps,
            'conversation_length': len(conversation_steps),
            'user_profile': user_profile,
            'program_recommended': program_recommended,
            'success': is_success,
            'total_tokens': total_tokens,
            'latency_ms': latency_ms,
            'user_input': user_input,
            'bot_response': bot_response
        }
        
        conversations.append(conversation)
    
    return conversations

def calculate_cost(tokens: Optional[int], model: str = "gpt-4") -> float:
    """Calculate approximate cost based on tokens."""
    if not tokens:
        return 0.0
    
    # Cost per 1K tokens
    costs = {
        "gpt-4": 0.03,
        "gpt-4-turbo": 0.01,
        "gpt-3.5-turbo": 0.002,
        "claude-3-5-sonnet": 0.003,
        "claude-3": 0.015
    }
    
    return (tokens / 1000) * costs.get(model, 0.01)
