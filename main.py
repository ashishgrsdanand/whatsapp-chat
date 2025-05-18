from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from twilio.rest import Client
import os
import dotenv

app=FastAPI()

# allow frontend to connet

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)



dotenv.load_dotenv()

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_NUMBER')
client = Client(account_sid, auth_token)

# websocket manager


# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket:WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"You: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

class MessageRequest(BaseModel):
    recipient_number: str
    message_body: str


@app.post("/send_message")
async def send_whatsapp_message(request: MessageRequest):
    try:
        message = client.messages.create(
            body=request.message_body,
            from_=twilio_number,
            to=f'whatsapp:{request.recipient_number}'
        )
        return {"status": "success", "message_sid": message.sid}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# WhatsApp webhook to receive replies
@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    from_number = form.get("From")
    body = form.get("Body")

    if from_number and body:
        await manager.broadcast(f"WhatsApp ({from_number}): {body}")
    return "OK"

 #whatsapp status callback
@app.post("/status_callback")
async def status_callback(request: Request):
    form = await request.form()
    message_sid = form.get("MessageSid")
    status = form.get("MessageStatus")
    to_number = form.get("To")
    from_number = form.get("From")

    if message_sid and status:
        await manager.broadcast(f"Status update for {message_sid}: {status} from {from_number} to {to_number}")
    return "OK"