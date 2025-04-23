from fastapi import FastAPI, HTTPException
import uvicorn
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.hazmat.primitives import serialization, hashes
import base64
import json
import os
from typing import List
from pymongo import MongoClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MONGO_URI = "mongodb://localhost:27017"
client = MongoClient(MONGO_URI)
db = client["package_measurement_db"]
history_collection = db["request_history"]

MEASUREMENTS_FILE = "measurements.json"
local_measurements = []

# Mapping of letters to numbers
alpha = {
    "_": 0, "a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8, "i": 9, "j": 10,
    "k": 11, "l": 12, "m": 13, "n": 14, "o": 15, "p": 16, "q": 17, "r": 18, "s": 19,
    "t": 20, "u": 21, "v": 22, "w": 23, "x": 24, "y": 25, "z": 26
}

def decode_value(encoded: str) -> int:
    """Convert encoded string to numeric value using alphabet mapping"""
    total = 0
    for char in encoded.lower():
        if char not in alpha:
            raise ValueError(f"Invalid character in encoded value: {char}")
        total += alpha[char]
    return total

app = FastAPI(title="Package Measurement API")

# Encryption setup
KEY_FILE = "encryption.key"
DATA_FILE = "measurements.encrypted"
encryption_key = None
measurements_data = []

PRIVATE_KEY_FILE = "private_key.pem"
PUBLIC_KEY_FILE = "public_key.pem"

def generate_rsa_keys():
    if not os.path.exists(PRIVATE_KEY_FILE) or not os.path.exists(PUBLIC_KEY_FILE):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open(PRIVATE_KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        public_key = private_key.public_key()
        with open(PUBLIC_KEY_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))

def load_private_key():
    with open(PRIVATE_KEY_FILE, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def load_public_key():
    with open(PUBLIC_KEY_FILE, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def initialize_encryption():
    global encryption_key
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as key_file:
            encryption_key = key_file.read()
    else:
        encryption_key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(encryption_key)
    return Fernet(encryption_key)

def encrypt_with_public_key(data: str) -> str:
    public_key = load_public_key()
    encrypted = public_key.encrypt(
        data.encode(),
        rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    return base64.b64encode(encrypted).decode()

def decrypt_with_private_key(data: str) -> str:
    private_key = load_private_key()
    decrypted = private_key.decrypt(
        base64.b64decode(data.encode()),
        rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )
    return decrypted.decode()

def parse_measurements(input_str: str) -> List[int]:
    logger.info(f"Processing input string: {input_str}")
    if not input_str:
        return []

    nums = []
    i = 0
    while i < len(input_str):
        c = input_str[i]
        if c not in alpha:
            raise ValueError(f"Invalid character in input: {c}")

        if c == 'z' and (i + 1) < len(input_str):
            next_c = input_str[i + 1]
            if next_c not in alpha:
                raise ValueError(f"Invalid character after z: {next_c}")
            z_value = 26 + alpha[next_c]
            nums.append(z_value)
            i += 2
        else:
            nums.append(alpha[c])
            i += 1

    results = []
    i = 0
    while i < len(nums):
        package_size = nums[i]
        i += 1
        package_total = 0
        for _ in range(package_size):
            if i < len(nums):
                package_total += nums[i]
                i += 1
        results.append(package_total)

    logger.debug(f"Package totals: {results}")
    return results

@app.on_event("startup")
async def startup_event():
    """Initialize encryption and load saved data"""
    global measurements_data , local_measurements
    logger.info("Starting up application")
    generate_rsa_keys()
    fernet = initialize_encryption()
    generate_rsa_keys()
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "rb") as f:
                encrypted_data = f.read()
                decrypted_data = fernet.decrypt(encrypted_data)
                measurements_data = json.loads(decrypted_data)
                logger.info("Successfully loaded saved measurements data")
        except Exception as e:
            logger.error(f"Error loading saved data: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Save data before shutdown"""
    logger.info("Shutting down application")
    fernet = Fernet(encryption_key)
    encrypted_data = fernet.encrypt(json.dumps(measurements_data).encode())
    with open(DATA_FILE, "wb") as f:
        f.write(encrypted_data)
    logger.info("Successfully saved measurements data")

@app.get("/convert-measurements/")
async def convert_measurements(input: str):
    try:
        result = parse_measurements(input)
        # Store original in MongoDB
        history_collection.insert_one({
            "input": input,
            "output": result
        })
        # Asymmetric encryption for local file
        encrypted_input = encrypt_with_public_key(input)
        encrypted_output = encrypt_with_public_key(json.dumps(result))
        record = {
            "input": encrypted_input,
            "output": encrypted_output
        }
        local_measurements.append(record)
        with open(MEASUREMENTS_FILE, "w") as f:
            json.dump(local_measurements, f, indent=2)
        logger.info(f"Processed measurement: {input} -> {result}")
        return result
    except Exception as e:
        logger.error(f"Error processing measurement: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/measurement-history/")
async def get_measurement_history():
    """Retrieve measurement history from MongoDB"""
    history = list(history_collection.find({}, {"_id": 0}))
    return history

@app.get("/decrypt-measurement/")
async def decrypt_measurement(record: dict):
    try:
        decrypted_input = decrypt_with_private_key(record["input"])
        decrypted_output = json.loads(decrypt_with_private_key(record["output"]))
        return {"input": decrypted_input, "output": decrypted_output}
    except Exception as e:
        logger.error(f"Error decrypting measurement: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("Main_APP:app", host="0.0.0.0", port=8000, reload=False)