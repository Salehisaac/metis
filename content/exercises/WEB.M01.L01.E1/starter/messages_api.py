from fastapi import FastAPI

app = FastAPI()

# In-memory data; the database arrives in WEB.M05.
# Ids grow over time, so a higher id means a newer message.
MESSAGES = [
    {"id": 1, "chat_id": 10, "sender": "ali", "text": "hi", "read": True},
    {"id": 2, "chat_id": 10, "sender": "sara", "text": "hello", "read": True},
    {"id": 3, "chat_id": 20, "sender": "omid", "text": "lunch?", "read": False},
    {"id": 4, "chat_id": 10, "sender": "ali", "text": "how are you?", "read": False},
    {"id": 5, "chat_id": 10, "sender": "sara", "text": "fine", "read": False},
    {"id": 6, "chat_id": 20, "sender": "ali", "text": "yes", "read": True},
]


# TODO: GET /chats/{chat_id}/messages  (see exercise.json for the contract)
