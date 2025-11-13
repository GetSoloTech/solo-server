from typing import Optional
from pydantic import BaseModel
import litserve as ls
from litserve.mcp import MCP

class CropStatusRequest(BaseModel):
    """
    Optional field name (e.g. 'North Field').
    If not provided, returns status for the main field.
    """
    field: Optional[str] = None

class CropStatusAPI(ls.LitAPI):
    def setup(self, device):
        pass

    def decode_request(self, request: CropStatusRequest):
        return request.field

    def predict(self, field_name: Optional[str]):
        # Mock status
        if field_name:
            return {"field": field_name, "status": "Healthy", "last_checked": "2024-07-20"}
        else:
            return {"field": "Main Field", "status": "Healthy", "last_checked": "2024-07-20"}

    def encode_response(self, output):
        return output

if __name__ == "__main__":
    api = CropStatusAPI(
        mcp=MCP(
            description="Returns the current crop status for a specified field (or main field if not specified)."
        )
    )
    server = ls.LitServer(api)
    server.run(port=8002) 