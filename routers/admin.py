from fastapi import APIRouter, Depends, HTTPException
import models, schemas, auth
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/pending-users", response_model=List[schemas.User])
async def get_pending_users(current_user: models.User = Depends(auth.get_current_admin)):
    return await models.User.find(models.User.is_approved == False).to_list()

@router.post("/approve/{user_id}")
async def approve_user(user_id: str, current_user: models.User = Depends(auth.get_current_admin)):
    user = await models.User.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_approved = True
    await user.save()
    return {"message": f"User {user.email} approved"}
