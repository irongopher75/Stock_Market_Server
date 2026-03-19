from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.db import models, schemas
from app.core import auth
from datetime import timedelta
from main import limiter

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=schemas.User)
@limiter.limit("5/minute")
async def register(request: Request, user_in: schemas.UserCreate):
    try:
        user = await models.User.find_one(models.User.email == user_in.email)
        if user:
            raise HTTPException(status_code=400, detail="User already registered")
        
        new_user = models.User(
            email=user_in.email,
            hashed_password=auth.get_password_hash(user_in.password),
            is_active=True,
            is_approved=False # Hotfix: require admin approval
        )
        await new_user.insert()
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        with open("server_error.log", "a") as f:
            f.write(f"Registration Error: {traceback.format_exc()}\n")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/token", response_model=schemas.Token)
@limiter.limit("10/minute")
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = await models.User.find_one(models.User.email == form_data.username)
        if not user or not auth.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_approved:
            raise HTTPException(status_code=403, detail="Account pending approval by Admin")
            
        access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        with open("server_error.log", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.post("/watchlist/{symbol}")
async def add_to_watchlist(symbol: str, current_user: models.User = Depends(auth.get_current_active_user)):
    symbol = symbol.upper()
    if current_user.watchlist is None:
        current_user.watchlist = []
    if symbol not in current_user.watchlist:
        current_user.watchlist.append(symbol)
        await current_user.save()
        
        # Proactively trigger WebSocket subscription if it's a new symbol
        from app.services.websocket_manager import ws_manager
        await ws_manager.subscribe_to_symbol(symbol)
        
    return current_user.watchlist

@router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, current_user: models.User = Depends(auth.get_current_active_user)):
    symbol = symbol.upper()
    if current_user.watchlist and symbol in current_user.watchlist:
        current_user.watchlist.remove(symbol)
        await current_user.save()
    return current_user.watchlist
