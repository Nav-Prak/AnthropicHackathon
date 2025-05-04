import os
import anthropic
import json
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def analyze_scan_with_claude(scan_results):
    if "assembly" in scan_results:
        assembly_code = scan_results["assembly"][:3000]
        prompt = f"""
You are a malware analyst. Analyze the following assembly code for:
- Indicators of compromise (e.g. suspicious syscalls, obfuscation)
- Malware behaviors (e.g. keylogging, persistence, exfiltration)
- Recommended mitigation steps

Assembly Snippet:
```
{assembly_code}
```

Respond strictly in JSON like this:
{{
  "risk_severity": "Low/Medium/High",
  "security_concerns": "...",
  "recommended_actions": "..."
}}
"""
        try:
            response = client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=800,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.content[0].text.strip())

        except Exception as e:
            print(f"Error analyzing assembly with Claude: {e}")
            return {
                "risk_severity": "Unknown",
                "security_concerns": "Assembly analysis failed.",
                "recommended_actions": "No suggestion available."
            }

    # Fallback: model scan without assembly
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
        return json.loads(response.content[0].text.strip())

    except Exception as e:
        print(f"Error analyzing metadata with Claude: {e}")
        return {
            "risk_severity": "Unknown",
            "security_concerns": "Analysis failed.",
            "recommended_actions": "No suggestions available."
        }
