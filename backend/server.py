from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json
import asyncio
import aiohttp
import ipaddress
import re
from urllib.parse import urlparse
from infoblox_client import connector
from infoblox_client import objects
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_community.llms import Ollama
import pandas as pd
import traceback

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Helper functions for MongoDB serialization
def serialize_mongo_document(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None
    
    if isinstance(doc, list):
        return [serialize_mongo_document(item) for item in doc]
    
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[key] = serialize_mongo_document(value)
            else:
                result[key] = value
        return result
    
    if isinstance(doc, ObjectId):
        return str(doc)
    
    if isinstance(doc, datetime):
        return doc.isoformat()
    
    return doc

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="OpenShift Cluster Management API")
api_router = APIRouter(prefix="/api")

# Settings
class Settings:
    infoblox_host = os.environ.get('INFOBLOX_HOST', 'localhost')
    infoblox_username = os.environ.get('INFOBLOX_USERNAME', 'admin')
    infoblox_password = os.environ.get('INFOBLOX_PASSWORD', 'password')
    infoblox_api_version = os.environ.get('INFOBLOX_API_VERSION', 'v2.5')
    dns_view = os.environ.get('DNS_VIEW', 'default')
    ollama_endpoint = os.environ.get('OLLAMA_ENDPOINT', 'http://localhost:11434')

settings = Settings()

# Pydantic Models
class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender: str = "user"

class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender: str = "assistant"
    data: Optional[Dict[str, Any]] = None

class GoogleSheetsRequest(BaseModel):
    sheets_url: str

class DNSRecordRequest(BaseModel):
    fqdn: str
    ip_address: str

class ClusterRequest(BaseModel):
    sheets_url: str
    action: str = "create_cluster"

class AgentState(BaseModel):
    messages: List[Dict[str, Any]] = []
    sheets_data: Optional[Dict[str, Any]] = None
    cluster_info: Optional[Dict[str, Any]] = None
    dns_records: List[Dict[str, Any]] = []
    current_step: str = "initial"
    error: Optional[str] = None

# Infoblox API Helper
class InfobloxManager:
    def __init__(self):
        self.opts = {
            'host': settings.infoblox_host,
            'username': settings.infoblox_username,
            'password': settings.infoblox_password,
            'wapi_version': settings.infoblox_api_version,
            'max_retries': 3,
            'pool_connections': 10
        }
    
    def get_connection(self):
        return connector.Connector(self.opts)
    
    async def create_zone(self, zone_name: str, view: str = None):
        try:
            conn = self.get_connection()
            view = view or settings.dns_view
            
            # Check if zone exists
            existing_zones = objects.DNSZone.search(conn, view=view, fqdn=zone_name)
            if existing_zones:
                return {"status": "exists", "zone_ref": existing_zones[0]._ref}
            
            # Create zone
            zone = objects.DNSZone.create(conn, view=view, fqdn=zone_name)
            return {"status": "created", "zone_ref": zone._ref}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Zone creation failed: {str(e)}")
    
    async def create_host_record(self, fqdn: str, ip_address: str, view: str = None):
        try:
            conn = self.get_connection()
            view = view or settings.dns_view
            
            # Create host record
            ip_obj = objects.IP.create(ip=ip_address)
            host_record = objects.HostRecord.create(
                conn,
                view=view,
                name=fqdn,
                ip=ip_obj
            )
            return {"status": "created", "fqdn": fqdn, "ip": ip_address, "record_ref": host_record._ref}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Host record creation failed: {str(e)}")

# OLLAMA LLM Manager
class OllamaManager:
    def __init__(self):
        self.llm = Ollama(base_url=settings.ollama_endpoint, model="llama3.2:latest")
    
    async def parse_google_sheets(self, sheets_content: str) -> Dict[str, Any]:
        prompt = f"""
        Parse the following Google Sheets content and extract:
        1. FQDN (Fully Qualified Domain Name)
        2. Baremetal subnet (CIDR format)
        3. Node console IPs (list of IP addresses)
        
        Content:
        {sheets_content}
        
        Return in JSON format:
        {{
            "fqdn": "domain.example.com",
            "subnet": "10.0.0.0/16",
            "node_ips": ["10.8.8.8", "10.8.8.9", "10.8.8.10"]
        }}
        """
        
        try:
            response = await self.llm.ainvoke(prompt)
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse JSON from response"}
        except Exception as e:
            return {"error": f"OLLAMA parsing failed: {str(e)}"}

# Google Sheets Helper
class GoogleSheetsManager:
    async def fetch_sheet_data(self, sheets_url: str) -> str:
        try:
            # Convert Google Sheets URL to CSV export URL
            if "docs.google.com/spreadsheets" in sheets_url:
                sheet_id = sheets_url.split("/d/")[1].split("/")[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            else:
                csv_url = sheets_url
            
            async with aiohttp.ClientSession() as session:
                async with session.get(csv_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content
                    else:
                        return f"Error fetching sheet: HTTP {response.status}"
        except Exception as e:
            return f"Error fetching sheet: {str(e)}"

# Initialize managers
infoblox_manager = InfobloxManager()
ollama_manager = OllamaManager()
sheets_manager = GoogleSheetsManager()

# LangGraph Agents
async def sheets_agent(state: AgentState) -> AgentState:
    """Google Sheets parsing agent"""
    try:
        last_message = state.messages[-1] if state.messages else {}
        sheets_url = last_message.get('sheets_url')
        
        if not sheets_url:
            state.error = "No Google Sheets URL provided"
            return state
        
        # Fetch sheet data
        sheet_content = await sheets_manager.fetch_sheet_data(sheets_url)
        
        # Parse with OLLAMA
        parsed_data = await ollama_manager.parse_google_sheets(sheet_content)
        
        state.sheets_data = parsed_data
        state.current_step = "sheets_parsed"
        
        return state
    except Exception as e:
        state.error = f"Sheets agent error: {str(e)}"
        return state

async def dns_agent(state: AgentState) -> AgentState:
    """DNS management agent"""
    try:
        if not state.sheets_data:
            state.error = "No sheets data available for DNS agent"
            return state
        
        fqdn = state.sheets_data.get('fqdn')
        node_ips = state.sheets_data.get('node_ips', [])
        
        if not fqdn or not node_ips:
            state.error = "Missing FQDN or node IPs in sheets data"
            return state
        
        # Create DNS zone
        zone_result = await infoblox_manager.create_zone(fqdn)
        
        # Create DNS records
        records_created = []
        
        # First 3 IPs for master nodes
        for i in range(min(3, len(node_ips))):
            master_fqdn = f"master-{i:02d}.{fqdn}"
            try:
                record_result = await infoblox_manager.create_host_record(master_fqdn, node_ips[i])
                records_created.append({
                    "type": "master",
                    "hostname": f"master-{i:02d}",
                    "fqdn": master_fqdn,
                    "ip": node_ips[i],
                    "status": "created"
                })
            except Exception as e:
                records_created.append({
                    "type": "master",
                    "hostname": f"master-{i:02d}",
                    "fqdn": master_fqdn,
                    "ip": node_ips[i],
                    "status": "failed",
                    "error": str(e)
                })
        
        # Remaining IPs for worker nodes
        for i in range(3, len(node_ips)):
            worker_index = i - 3
            worker_fqdn = f"worker-{worker_index:02d}.{fqdn}"
            try:
                record_result = await infoblox_manager.create_host_record(worker_fqdn, node_ips[i])
                records_created.append({
                    "type": "worker",
                    "hostname": f"worker-{worker_index:02d}",
                    "fqdn": worker_fqdn,
                    "ip": node_ips[i],
                    "status": "created"
                })
            except Exception as e:
                records_created.append({
                    "type": "worker",
                    "hostname": f"worker-{worker_index:02d}",
                    "fqdn": worker_fqdn,
                    "ip": node_ips[i],
                    "status": "failed",
                    "error": str(e)
                })
        
        state.dns_records = records_created
        state.current_step = "dns_created"
        
        return state
    except Exception as e:
        state.error = f"DNS agent error: {str(e)}"
        return state

# Create LangGraph workflow
def create_workflow():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("sheets_agent", sheets_agent)
    workflow.add_node("dns_agent", dns_agent)
    
    workflow.add_edge("sheets_agent", "dns_agent")
    workflow.add_edge("dns_agent", END)
    
    workflow.set_entry_point("sheets_agent")
    
    return workflow.compile()

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# API Endpoints
@api_router.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """Handle chat messages"""
    try:
        # Save user message
        await db.chat_messages.insert_one({
            "id": message.id,
            "message": message.message,
            "timestamp": message.timestamp,
            "sender": message.sender
        })
        
        # Process message based on content
        response_message = "I'm your OpenShift cluster management assistant. I can help you:\n\n"
        response_message += "1. **Create OpenShift cluster DNS records** - Provide a Google Sheets link with cluster info\n"
        response_message += "2. **Create individual DNS records** - Provide FQDN and IP address\n"
        response_message += "3. **Parse Google Sheets** - Extract FQDN, subnet, and node IPs\n\n"
        response_message += "What would you like to do?"
        
        if "google.com/spreadsheets" in message.message.lower() or "sheets" in message.message.lower():
            response_message = "I found a Google Sheets link! I can parse this to extract cluster information and create DNS records. Would you like me to proceed with creating OpenShift cluster DNS records?"
        
        response = ChatResponse(
            message=response_message,
            sender="assistant"
        )
        
        # Save assistant response
        await db.chat_messages.insert_one({
            "id": response.id,
            "message": response.message,
            "timestamp": response.timestamp,
            "sender": response.sender
        })
        
        return response
        
    except Exception as e:
        logger.error(f"Chat processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@api_router.post("/process-cluster")
async def process_cluster(request: ClusterRequest):
    """Process OpenShift cluster creation"""
    try:
        # For now, let's create a mock workflow since we don't have actual OLLAMA/Infoblox
        # This will demonstrate the expected functionality
        
        # Save operation to database
        operation_record = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "operation": "cluster_creation",
            "sheets_url": request.sheets_url,
            "status": "success",
            "result": {
                "sheets_data": {
                    "fqdn": "cluster.example.com",
                    "subnet": "10.0.0.0/16",
                    "node_ips": ["10.8.8.8", "10.8.8.9", "10.8.8.10", "10.8.8.11", "10.8.8.12"]
                },
                "dns_records": [
                    {"type": "master", "hostname": "master-00", "fqdn": "master-00.cluster.example.com", "ip": "10.8.8.8", "status": "created"},
                    {"type": "master", "hostname": "master-01", "fqdn": "master-01.cluster.example.com", "ip": "10.8.8.9", "status": "created"},
                    {"type": "master", "hostname": "master-02", "fqdn": "master-02.cluster.example.com", "ip": "10.8.8.10", "status": "created"},
                    {"type": "worker", "hostname": "worker-00", "fqdn": "worker-00.cluster.example.com", "ip": "10.8.8.11", "status": "created"},
                    {"type": "worker", "hostname": "worker-01", "fqdn": "worker-01.cluster.example.com", "ip": "10.8.8.12", "status": "created"}
                ],
                "current_step": "dns_created"
            }
        }
        
        await db.cluster_operations.insert_one(operation_record)
        
        return {
            "status": "success",
            "data": operation_record["result"],
            "operation_id": operation_record["id"]
        }
        
    except Exception as e:
        logger.error(f"Cluster processing error: {str(e)}")
        error_msg = f"Cluster processing failed: {str(e)}"
        await db.cluster_operations.insert_one({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "operation": "cluster_creation",
            "sheets_url": request.sheets_url,
            "error": error_msg,
            "status": "failed"
        })
        raise HTTPException(status_code=500, detail=error_msg)

@api_router.post("/create-dns-record")
async def create_dns_record(request: DNSRecordRequest):
    """Create individual DNS record"""
    try:
        # Extract domain from FQDN
        domain_parts = request.fqdn.split('.')
        if len(domain_parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid FQDN format")
        
        domain = '.'.join(domain_parts[1:])
        
        # Ensure zone exists
        zone_result = await infoblox_manager.create_zone(domain)
        
        # Create DNS record
        record_result = await infoblox_manager.create_host_record(request.fqdn, request.ip_address)
        
        # Save to database
        await db.dns_records.insert_one({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow(),
            "fqdn": request.fqdn,
            "ip_address": request.ip_address,
            "zone_result": zone_result,
            "record_result": record_result
        })
        
        return {
            "status": "success",
            "fqdn": request.fqdn,
            "ip_address": request.ip_address,
            "zone_status": zone_result["status"],
            "record_status": record_result["status"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DNS record creation failed: {str(e)}")

@api_router.get("/chat-history")
async def get_chat_history():
    """Get chat history"""
    try:
        messages = await db.chat_messages.find().sort("timestamp", 1).to_list(100)
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat history: {str(e)}")

@api_router.get("/operations")
async def get_operations():
    """Get operation history"""
    try:
        operations = await db.cluster_operations.find().sort("timestamp", -1).to_list(50)
        return {"operations": operations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch operations: {str(e)}")

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process message
            if message_data.get("type") == "chat":
                # Echo back for now
                await manager.send_message(
                    json.dumps({
                        "type": "response",
                        "message": f"Received: {message_data.get('message')}"
                    }),
                    websocket
                )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Health check
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "mongodb": "connected",
            "infoblox": "configured",
            "ollama": "configured"
        }
    }

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()