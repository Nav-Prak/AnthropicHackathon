# modules/mcp_logger.py

from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class MCPRecord:
    model_name: str
    provider: str
    original_prompt: str
    adversarial_prompt: str
    model_response: str
    risk_score: int
    violation_type: str
    evaluation_comments: str
    attack_type: str
    tags: list
    timestamp: str = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)

def save_mcp_record(record: MCPRecord, filepath="mcp_logs.json"):
    import json, os
    records = []

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                records = json.load(f)
            except:
                records = []

    records.append(record.to_dict())

    with open(filepath, "w") as f:
        json.dump(records, f, indent=4)
