"""Optional OpenAI-powered placement assistance. PLACIFY remains functional without a key."""
import os

def summarize_drive(drive):
    key=os.getenv('OPENAI_API_KEY')
    if not key: return None
    try:
        from openai import OpenAI
        client=OpenAI(api_key=key)
        response=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5-mini'),input=f"Summarize this placement opportunity for students in concise bullet points. Company: {drive.company.name}. Role: {drive.job_role}. Title: {drive.title}. Description: {drive.description}. Eligibility: {drive.eligibility_description}. Package: {drive.salary_package} LPA.")
        return response.output_text
    except Exception:
        return None
