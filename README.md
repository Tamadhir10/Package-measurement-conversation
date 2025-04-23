# API-for-Package-Measurement-Conversation

This project is a FastAPI-based web API for converting encoded package measurement strings into numeric totals. It supports secure, persistent storage of request/response history in MongoDB and also saves encrypted records locally using asymmetric (RSA) encryption.

## Features

- **Measurement Conversion:** Converts encoded strings (e.g., `dz_a_aazzaaa`) into a list of totals for each package, using custom character-to-number mapping and package size rules.
- **Z-Combinations:** Handles consecutive `z` characters as part of package size calculation (e.g., `zza` means size = 26 + 26 + 1).
- **Zero Handling:** Treats underscores (`_`) as zero values.
- **Persistent History:** Stores all conversion requests and results in MongoDB (original, unencrypted).
- **Encrypted Local Storage:** Saves encrypted input/output records to a local JSON file using RSA public key encryption.
- **Asymmetric Encryption:** Uses RSA keys for encrypting and decrypting local measurement records.

## How It Works

1. **Package Size:** Determined by summing all leading `z` characters and the next character's value.
2. **Value Mapping:** Each character is mapped to a number (`a`=1, `b`=2, ..., `z`=26, `_`=0).
3. **Package Calculation:** For each package, the size indicator(s) are skipped, and the next `package_size` values are summed.
4. **Multiple Packages:** The process repeats for the remainder of the string.
5. **Encrypted Storage:** Each input/output pair is encrypted with the public key and stored in `measurements.json`. MongoDB stores the original data.

## Example

**Input:**  
`dz_a_aazzaaa`

- Package size is determined by the first character and z-combinations.
- Underscores (`_`) are treated as zero.
- The API processes each package and returns a list of totals.

## API Endpoints

- `GET /convert-measurements/?input=...`  
  Converts the input string and returns the result.

- `GET /measurement-history/`  
  Retrieves the history of all conversion requests and results.

- `GET /decrypt-measurement/`  
  (Optional) Decrypts a record from the encrypted local file using the private key.

## Setup

1. **Install dependencies:**
    bash
    pip install fastapi uvicorn pymongo cryptography

2. **Start MongoDB:**  
   Ensure MongoDB is running locally, or update the connection string in `Main_APP.py`.

3. **Run the API:**
 bash
    python Main_APP.py
4. **Access the API docs:**  
   Visit [http://localhost:8888/docs](http://localhost:8888/docs) for interactive documentation.

## Project Structure

- `Main_APP.py` - Main FastAPI application and logic
- `measurements.json` - Encrypted local storage of measurement records
- `private_key.pem` / `public_key.pem` - RSA keys for encryption/decryption
- `README.md` - Project documentation

## License

MIT License
