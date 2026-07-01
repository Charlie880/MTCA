# main.py

import uuid
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends

from app.core.models import UserAuth, ChatMessage
from app.core.auth import hash_password, verify_password, create_access_token, verify_token
from app.db.clients import get_mongo_db
from app.db.operations import get_tenant_config
from app.langgraph.graph import compiled_rag_graph, checkpointer

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup checkpointer indexes
    await checkpointer.setup()

    db = get_mongo_db()
    # Enforce Unique Email Constraint
    await db["users"].create_index("email", unique=True)
    logging.info("MongoDB: Verified unique index on User emails.")
    yield

app = FastAPI(title="Multi-Tenant AI", lifespan=lifespan)

@app.post("/auth/authenticate")
async def authenticate_user(user: UserAuth):
    db = get_mongo_db()
    users_col = db["users"]
    
    existing_user = await users_col.find_one({"email": user.email})
    
    if existing_user:
        if not verify_password(user.password, existing_user["password"]):
            raise HTTPException(status_code=401, detail="Incorrect password.")
        
        if existing_user["org_id"] != user.org_id:
            raise HTTPException(status_code=403, detail="Email registered to a different organization.")
            
        user_id = existing_user["user_id"]
        message = f"Welcome back, {existing_user['username']}!"
    else:
        user_id = str(uuid.uuid4())
        new_user = {
            "user_id": user_id,
            "org_id": user.org_id,
            "branch_id": user.branch_id,
            "username": user.username,
            "email": user.email,
            "password": hash_password(user.password)
        }
        await users_col.insert_one(new_user)
        message = "Account created successfully!"

    token = create_access_token({
        "sub": user.email, 
        "org": user.org_id, 
        "branch": user.branch_id, 
        "user": user.username,
        "user_id": user_id 
    })
    
    return {"token": token, "message": message, "user_id": user_id}

@app.post("/chat")
async def chat_endpoint(
    request: ChatMessage,
    token_payload: dict = Depends(verify_token)
):
    org_id = token_payload["org"]
    branch_id = token_payload["branch"]
    user_id = token_payload["user_id"]

    try:

        tenant_config = await get_tenant_config(
            org_id,
            branch_id
        )

        if not tenant_config:
            raise HTTPException(
                status_code=404,
                detail="Inactive organization/branch."
            )


        username = token_payload.get("user")
        user_email = token_payload.get("sub")


        logging.info(
            f"""
GRAPH INPUT
-----------
org_id={org_id}
branch_id={branch_id}
username={username}
email={user_email}
user_id={user_id}
"""
        )


        initial_state = {

            "messages": [
                ("user", request.text)
            ],


            # Tenant
            "org_id": org_id,
            "branch_id": branch_id,


            # Identity
            "username": username,
            "user_email": user_email,
            "user_id": user_id,


            # Config
            "mongo_rules": tenant_config,


            # Workflow defaults
            "active_flow": None,
            "flow_complete": False,


            # Lead defaults
            "lead_state": {},
            "lead_saved_flag": False,


            # Response
            "final_response": "",

        }


        graph_config = {
            "configurable": {
                "thread_id": user_id
            }
        }


        result = await compiled_rag_graph.ainvoke(
            initial_state,
            config=graph_config
        )


        return {
            "response": result.get("final_response"),

            "router": {
                "intent": result.get("intent"),
                "search_query": result.get("search_query"),
                "routing_examples": result.get("routing_examples")
            }
        }


    except Exception as e:

        logging.error(
            f"Error processing graph: {str(e)}"
        )

        logging.error(
            traceback.format_exc()
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )