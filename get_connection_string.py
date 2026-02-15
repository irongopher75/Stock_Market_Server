from pymongo import MongoClient
import os
from dotenv import load_dotenv
import time

load_dotenv()
url = os.getenv("MONGODB_URL")

try:
    print(f"Connecting to: {url.split('@')[1]}") # Print host part only for privacy/debug
    client = MongoClient(url)
    # Force connection
    client.admin.command('ping')
    
    print("\n--- CONNECTION DETAILS ---")
    print(f"Nodes: {client.nodes}")
    print(f"Replica Set Name: {client.options.replica_set_name}")
    
    # Construct standard string
    hosts = ",".join([f"{h[0]}:{h[1]}" for h in client.nodes])
    username = client.options.username
    password = client.options.password
    db = client.options.default_database or "stock_db"
    rs = client.options.replica_set_name
    
    std_str = f"mongodb://{username}:{password}@{hosts}/{db}?ssl=true&replicaSet={rs}&authSource=admin&retryWrites=true&w=majority"
    print("\n--- STANDARD CONNECTION STRING ---")
    print(std_str)
    
except Exception as e:
    print(f"Error: {e}")
