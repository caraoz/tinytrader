from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, PositiveInt
import logging

app = FastAPI()

# Setup basic logging
logging.basicConfig(level=logging.INFO)

# Simulated in-memory database for users
users = {
    "user1": {"balance": 1000},
    "user2": {"balance": 2000},
    # Add more users here
}

# Pydantic model for updating user balance
class BalanceUpdate(BaseModel):
    balance: PositiveInt = Field(..., example=500)

# API endpoint to get user details
@app.get("/user/{user_id}")
async def get_user(user_id: str):
    if user_id in users:
        logging.info(f"Fetching details for user {user_id}")
        return users[user_id]
    logging.warning(f"User {user_id} not found")
    raise HTTPException(status_code=404, detail="User not found")

# API endpoint to update user balance (e.g., after a trade)
@app.post("/user/{user_id}/update_balance/")
async def update_balance(user_id: str, balance_update: BalanceUpdate):
    if user_id in users:
        users[user_id]["balance"] = balance_update.balance
        logging.info(f"Updated balance for user {user_id}: {balance_update.balance}")
        return {"status": "Balance updated"}
    logging.warning(f"Attempt to update balance for non-existent user {user_id}")
    raise HTTPException(status_code=404, detail="User not found")

# Root endpoint for health check
@app.get("/")
def read_root():
    return {"message": "User Management Service is running"}

# Graceful shutdown to handle cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down User Management Service...")
    # Add any necessary cleanup logic here

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8007)