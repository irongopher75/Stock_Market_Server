import asyncio
import motor.motor_asyncio
from beanie import init_beanie
import os
from dotenv import load_dotenv
import bcrypt

# Add parent dir to path if needed (or just run from root)
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import User

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL")

async def create_admin():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    await init_beanie(database=client.get_default_database(), document_models=[User])
    
    email = "vishnu@123.com"
    password = "Achieve@2025"
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user = await User.find_one(User.email == email)
    if user:
        user.hashed_password = hashed_password
        user.is_superuser = True
        user.is_approved = True
        await user.save()
        print(f"Admin {email} updated.")
    else:
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            is_approved=True
        )
        await new_user.insert()
        print(f"Admin {email} created.")

if __name__ == "__main__":
    asyncio.run(create_admin())
