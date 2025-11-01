import asyncio
import json
import os
from asyncio.subprocess import PIPE, create_subprocess_exec

class MCPClient:
    def __init__(self, command: str, args: list, env: dict = None):
        self.command = command
        self.args = args
        self.env = {**(env or {}), **os.environ}
        self.proc = None
        self._id_counter = 1
        self._pending_responses = {}

    async def start(self):
        """Start the MCP server subprocess"""
        self.proc = await create_subprocess_exec(
            self.command, *self.args,
            stdin=PIPE, stdout=PIPE, stderr=PIPE,
            env=self.env
        )
        asyncio.create_task(self._read_stdout())

    async def _read_stdout(self):
        """Listen for responses from MCP server"""
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            try:
                data = json.loads(line)
                # Match responses with pending requests
                if 'id' in data and data['id'] in self._pending_responses:
                    fut = self._pending_responses.pop(data['id'])
                    fut.set_result(data)
            except json.JSONDecodeError:
                print("STDOUT:", line.decode().strip())

    async def call(self, method: str, params: dict):
        """Send a JSON-RPC request to MCP server"""
        req_id = self._id_counter
        self._id_counter += 1
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        fut = asyncio.get_event_loop().create_future()
        self._pending_responses[req_id] = fut
        self.proc.stdin.write((json.dumps(request) + "\n").encode())
        await self.proc.stdin.drain()
        response = await fut
        if 'error' in response:
            raise Exception(response['error'])
        return response.get('result')
