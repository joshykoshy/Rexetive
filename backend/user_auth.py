import sqlite3
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv
from pysui import SyncClient, SuiConfig, handle_result
from pysui.sui.sui_txn import SyncTransaction
from pysui.sui.sui_types import SuiAddress, ObjectID, SuiU64
from pysui.sui.sui_types.bcs import ObjectReference, Address, Digest
from blockchain_utils import submit_to_chain, get_submission_from_chain
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  
PACKAGE_ID = os.getenv("PREDICTIONS_PACKAGE_ID")
MODULE_NAME = os.getenv("PREDICTIONS_MODULE_NAME")
SUI_RPC_URL = os.getenv("SUI_RPC_URL")
SUI_PRIVATE_KEY = os.getenv("SUI_PRIVATE_KEY")
DATABASE_URL = "users.db"

sui_config = SuiConfig.user_config(
    rpc_url=SUI_RPC_URL,
    prv_keys=[SUI_PRIVATE_KEY]
)
sui_client = SyncClient(sui_config)

def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        wallet_address TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reputation_created BOOLEAN DEFAULT FALSE
    )
    ''')
    conn.commit()
    conn.close()

init_db()

class User(BaseModel):
    wallet_address: str
    created_at: datetime
    reputation_created: bool

class ReputationStats(BaseModel):
    reputation_points: int
    nft_count: int
    submissions_accepted: int
    wallet: str

def get_user(wallet_address: str):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT wallet_address, created_at, reputation_created FROM users WHERE wallet_address = ?", 
        (wallet_address,)
    )
    user_data = cursor.fetchone()

    if not user_data:
        now = datetime.now()
        cursor.execute(
            "INSERT INTO users (wallet_address, created_at, reputation_created) VALUES (?, ?, ?)",
            (wallet_address, now, False)
        )
        conn.commit()
        user_data = (wallet_address, now, False)
    
    conn.close()
    
    return User(
        wallet_address=user_data[0],
        created_at=user_data[1] if isinstance(user_data[1], datetime) else datetime.fromisoformat(user_data[1]),
        reputation_created=bool(user_data[2])
    )

def create_blockchain_reputation(wallet_address: str):
    try:
        tx = SyncTransaction(client=sui_client)
        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::create_user_reputation",
            arguments=[SuiAddress(wallet_address)]
        )
        result = handle_result(tx.execute())
        
        if result and hasattr(result, 'effects') and result.effects.status.status == "success":
            conn = sqlite3.connect(DATABASE_URL)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET reputation_created = TRUE WHERE wallet_address = ?", 
                (wallet_address,)
            )
            conn.commit()
            conn.close()
            return True
        return False
    except Exception as e:
        print(f"Error creating reputation on blockchain: {str(e)}")
        return False

async def get_user_reputation(wallet_address: str):
    try:
        objects_result = sui_client.get_objects(address=wallet_address)
        reputation_object_id = None
        objects_result = handle_result(objects_result)

        for obj in objects_result.data:
            if obj.object_type == f"{PACKAGE_ID}::{MODULE_NAME}::UserReputation":
                reputation_object_id = obj.object_id
                break
        if not reputation_object_id:
            print("No reputation object found for this wallet address.")
            return None
        
        reputation_object_id = ObjectID(reputation_object_id)
        
        tx = SyncTransaction(client=sui_client)
        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::get_user_stats",
            arguments=[reputation_object_id]
        )
        result = handle_result(tx.execute())
        
        if result and hasattr(result, 'effects') and result.effects.status.status == "success":
            if hasattr(result, 'events'):
                for event in result.events:
                    if event.event_type == f"{PACKAGE_ID}::{MODULE_NAME}::UserStatsViewed":
                        return ReputationStats(
                            nft_count=int(event.parsed_json['nft_count']),
                            reputation_points=int(event.parsed_json['reputation_points']),
                            submissions_accepted=int(event.parsed_json['submissions_accepted']),
                            wallet=wallet_address
                        )
        return None
    except Exception as e:
        print(f"Error fetching reputation from blockchain: {str(e)}")
        return None

async def update_user_reputation(wallet_address: str, points: int, nft_minted: bool):
    try:
        objects_result = sui_client.get_objects(address=wallet_address)
        reputation_object_id = None
        objects_result = handle_result(objects_result)

        for obj in objects_result.data:
            if obj.object_type == f"{PACKAGE_ID}::{MODULE_NAME}::UserReputation":
                reputation_object_id = obj.object_id
                break
        if not reputation_object_id:
            print("No reputation object found for this wallet address.")
            return None
        
        reputation_object_id = ObjectID(reputation_object_id)

        tx = SyncTransaction(client=sui_client)
        tx.move_call(
            target=f"{PACKAGE_ID}::{MODULE_NAME}::update_reputation",
            arguments=[
                reputation_object_id, 
                SuiU64(points),
                bool(nft_minted)
            ]
        )
        result = tx.execute()
        result = handle_result(result)

        if result and hasattr(result, 'effects') and result.effects.status.status == "success":
            print("Reputation updated successfully.")
            return True
        return False
    except Exception as e:
        print(f"Error updating reputation on blockchain: {str(e)}")
        return False

async def get_current_user(wallet_address: str = Header(..., alias="X-Wallet-Address")):
    """
    Dependency to extract wallet address from a custom header
    and retrieve or create the corresponding user.
    """
    if not wallet_address or not wallet_address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Invalid wallet address format")
    
    user = get_user(wallet_address)
    
    # Create blockchain reputation if needed
    if not user.reputation_created:
        reputation_created = create_blockchain_reputation(user.wallet_address)
        if reputation_created:
            user.reputation_created = True
    
    return user

def add_auth_routes(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/me", response_model=User)
    async def read_users_me(current_user: User = Depends(get_current_user)):
        return current_user
        
    @app.get("/me/reputation", response_model=ReputationStats)
    async def read_user_reputation(current_user: User = Depends(get_current_user)):
        reputation = await get_user_reputation(current_user.wallet_address)
        if not reputation:
            raise HTTPException(status_code=404, detail="Reputation not found")
        return reputation