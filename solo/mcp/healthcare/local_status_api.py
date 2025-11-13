from typing import Optional
from pydantic import BaseModel
import litserve as ls
from litserve.mcp import MCP

class PatientCountRequest(BaseModel):
    """
    Optional department name (e.g. 'Cardiology').
    If not provided, returns total patient count.
    """
    department: Optional[str] = None

class PatientCountAPI(ls.LitAPI):
    def setup(self, device):
        pass

    def decode_request(self, request: PatientCountRequest):
        return request.department

    def predict(self, department: Optional[str]):
        # Mock count
        if department:
            return {"department": department, "patient_count": 42}
        else:
            return {"department": "All", "patient_count": 123}

    def encode_response(self, output):
        return output

if __name__ == "__main__":
    api = PatientCountAPI(
        mcp=MCP(
            description="Returns the current patient count for a specified department (or total if not specified)."
        )
    )
    server = ls.LitServer(api)
    server.run(port=8003) 