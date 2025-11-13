from datetime import datetime
from typing import Optional

from pydantic import BaseModel
import pytz
import litserve as ls
from litserve.mcp import MCP

class LocalTimeRequest(BaseModel):
    """
    Optional timezone in Olson format (e.g. 'America/Los_Angeles').
    If not provided, uses the server’s local timezone.
    """
    timezone: Optional[str] = None

class LocalTimeAPI(ls.LitAPI):
    def setup(self, device):
        # no model to load here
        pass

    def decode_request(self, request: LocalTimeRequest):
        # pass through the timezone string
        return request.timezone

    def predict(self, tz_name: Optional[str]):
        # determine timezone
        if tz_name:
            try:
                tz = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                return {"error": f"Unknown timezone '{tz_name}'"}
        else:
            tz = datetime.now().astimezone().tzinfo
        # get current time
        now = datetime.now(tz)
        return {"local_time": now.strftime("%Y-%m-%d %H:%M:%S %Z")}

    def encode_response(self, output):
        # output is already JSON‐serializable
        return output

if __name__ == "__main__":
    api = LocalTimeAPI(
        mcp=MCP(
            description="Returns the server’s current local time, optionally in a specified timezone."
        )
    )
    server = ls.LitServer(api)
    server.run(port=8001)
