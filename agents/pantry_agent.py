import sys
import os
import json
from typing import Dict, List, Any
from datetime import datetime
import openai
import asyncio
from asyncio.subprocess import PIPE, create_subprocess_exec
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPEN_AI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)



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

async def main():
    agent = PantryAgent(None)

    # Start MCP client
    await agent.setup_mcp(
        command="/opt/anaconda3/envs/py312/bin/uvx",
        args=["mcp-google-sheets@latest"],
        env={
            "SERVICE_ACCOUNT_PATH": "/Users/zerongpeh/...json",
            "DRIVE_FOLDER_ID": "1a0SQa3QWfAib3SY6FScoeBJdtDjBpLOJ"
        }
    )

    # Call GPT and get a spreadsheet tool response
    response = await agent.process_query("Show me my pantry spreadsheet.")
    print(response)
    
class PantryAgent:

    def __init__(self, mcp_client: MCPClient, name: str = "Pantry Manager"):
        self.name = name
        self.mcp_client = mcp_client
        self.system_prompt = (
            """You are an expert Google Sheets Pantry Manager with access to real-time pantry data. Your role is to help user retrieve, add, remove, update, their pantries with ingredients.
             You have access to these tools:
             - create_spreadsheet: Creates a new spreadsheet
             - get_sheet_data: Reads data from a range in a sheet
             - update_cells: Writes data to a specific range. Overwrites existing data
             - add_rows: Appends rows to the end of a sheet (after the last row with data)
             - add_columns: Adds columns to a sheet
             
             Guidelines:
             - Utilize chain of thought processing to understand user intent and only use the relevant tool when necessary.
             """
        )

    async def setup_mcp(self, command, args, env):
        """Start the MCP client"""
        self.mcp_client = MCPClient(command=command, args=args, env=env)
        await self.mcp_client.start()
        print("✅ MCP Client started successfully")


    async def _execute_tool(self, tool_name: str, arguments: dict):
        return await self.mcp_client.call(tool_name, arguments)

    async def process_query(self, user_query: str):
        try:
            # 1️⃣ Ask GPT what tool to call
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_query}
            ]
            response = client.chat.completions.create(
                model="gpt-5-nano",
                messages=messages,
            )
            message = response.choices[0].message
            # 2️⃣ Here you would parse GPT's tool call (simplest: extract JSON in message)
            # For now, let's assume the user query directly maps to a tool:
            # e.g., {"tool": "listSpreadsheets", "args": {}}
            # In real use, GPT can return {"tool": "get_sheet_data", "args": {"range": "A1:C10"}}
            # For example purposes, we skip GPT parsing
            # 3️⃣ Call MCP server
            # result = await self._execute_tool(tool_name, tool_args)
            # return result
            return {"success": True, "response": message.content, "query": user_query, "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"success": False, "error": str(e), "response": "Error processing request."}
       
       




asyncio.run(main())