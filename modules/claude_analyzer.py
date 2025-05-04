# modules/claude_analyzer.py

import os
import anthropic
from dotenv import load_dotenv

# Load API key
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def analyze_scan_with_claude(scan_results):
    """
    Sends model scan results to Claude to get a professional risk analysis.

    Args:
        scan_results (dict): Dictionary from scan_model_file()

    Returns:
        dict: Claude's security assessment
    """

    # Create a clean structured summary for Claude
    summary_for_claude = f"""
You are an AI security auditor.

Analyze the following scanned ML model file and provide:
- A risk severity rating (Low, Medium, High)
- Detailed security concerns
- Recommended remediation actions (if any)

---
File Information:
- Filename: {scan_results.get('filename', 'Unknown')}
- File Type: {scan_results.get('file_type', 'Unknown')}
- Framework: {scan_results.get('framework', 'Unknown')}
- Detected Risks: {", ".join(scan_results.get('risks_detected', [])) if scan_results.get('risks_detected') else 'None'}
---

Format your output in **strict JSON** like this:

{{
  "risk_severity": "Low/Medium/High",
  "security_concerns": "Short paragraph explaining concerns",
  "recommended_actions": "Short paragraph suggesting mitigation"
}}

Respond only with JSON. No extra commentary.
"""

    try:
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=800,
            temperature=0,
            system=summary_for_claude,
            messages=[
                {"role": "user", "content": "Please provide your risk assessment in JSON."}
            ]
        )

        output_text = response.content[0].text.strip()

        # Parse the returned JSON
        import json
        assessment = json.loads(output_text)
        return assessment

    except Exception as e:
        print(f"Error analyzing with Claude: {e}")
        # Safe fallback if Claude fails
        return {
            "risk_severity": "Unknown",
            "security_concerns": "Analysis failed.",
            "recommended_actions": "No suggestions available."
        }
