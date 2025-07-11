from typing import Optional
from pydantic import BaseModel
import litserve as ls
from litserve.mcp import MCP

class MachineStatusRequest(BaseModel):
    """
    Optional machine name (e.g. 'Conveyor A').
    If not provided, returns status for the main machine.
    """
    machine: Optional[str] = None

class MachineStatusAPI(ls.LitAPI):
    def setup(self, device):
        pass

    def decode_request(self, request: MachineStatusRequest):
        return request.machine

    def predict(self, machine_name: Optional[str]):
        # Mock status
        if machine_name:
            return {"machine": machine_name, "status": "Running", "last_checked": "2024-07-20"}
        else:
            return {"machine": "Main Machine", "status": "Running", "last_checked": "2024-07-20"}

    def encode_response(self, output):
        return output

if __name__ == "__main__":
    api = MachineStatusAPI(
        mcp=MCP(
            description="Returns the current status for a specified machine (or main machine if not specified)."
        )
    )
    server = ls.LitServer(api)
    server.run(port=8004) 