from typing import Optional
from pydantic import BaseModel
import litserve as ls
from litserve.mcp import MCP

class AttendanceRequest(BaseModel):
    """
    Optional class name (e.g. 'Math 101').
    If not provided, returns attendance for the main class.
    """
    class_name: Optional[str] = None

class AttendanceAPI(ls.LitAPI):
    def setup(self, device):
        pass

    def decode_request(self, request: AttendanceRequest):
        return request.class_name

    def predict(self, class_name: Optional[str]):
        # Mock attendance
        if class_name:
            return {"class": class_name, "attendance": 28, "date": "2024-07-20"}
        else:
            return {"class": "Main Class", "attendance": 30, "date": "2024-07-20"}

    def encode_response(self, output):
        return output

if __name__ == "__main__":
    api = AttendanceAPI(
        mcp=MCP(
            description="Returns the current attendance for a specified class (or main class if not specified)."
        )
    )
    server = ls.LitServer(api)
    server.run(port=8005) 