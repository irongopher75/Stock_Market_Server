import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

# Diagnostics for querySrv ECONNREFUSED
async def test_connection():
    load_dotenv()
    uri = os.getenv("MONGODB_URL")
    if not uri:
        print("❌ Error: MONGODB_URL not found in .env")
        return

    print(f"Testing connection to: {uri[:30]}...")
    
    # Try with srv_max_hosts=1 if DNS is flaky
    client = motor.motor_asyncio.AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    
    try:
        print("Pinging...")
        await client.admin.command('ping')
        print("✅ Successfully connected to MongoDB Atlas!")
    except Exception as e:
        print(f"❌ Connection Failed: {str(e)}")
        print("\nPossible Causes:")
        print("1. IP Whitelist: Check if your current IP is whitelisted in Atlas.")
        print("2. DNS Issues: Your network/VPN might be blocking SRV records.")
        print("3. Firewall: Port 27017 must be open.")
        
        if "ECONNREFUSED" in str(e):
            print("\nTIP: Since you are seeing ECONNREFUSED on the SRV record, try the 'Standard Connection String' (without +srv) in Atlas if DNS issues persist.")

if __name__ == "__main__":
    asyncio.run(test_connection())
