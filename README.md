# Snowflake Google Sheets Integration

This project provides a backend API service that connects Google Sheets to Snowflake, allowing you to fetch and display Snowflake data in your Google Sheets.

## Setup Instructions

1. Clone this repository
2. Create a `.env` file with your Snowflake credentials (use `.env.example` as a template)
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python app.py
   ```

## Docker Setup

1. Build the Docker image:
   ```bash
   docker build -t snowflake-api .
   ```

2. Run the container:
   ```bash
   docker run -p 5000:5000 --env-file .env snowflake-api
   ```

## Security Notes

- Never commit the `.env` file
- Generate a secure API key for authentication
- Keep your Snowflake credentials secure
- Use HTTPS in production

## API Documentation

### Endpoint: `/api/data`
- Method: POST
- Authentication: Bearer token
- Request body:
  ```json
  {
    "customer_id": "CUSTOMER_ID_HERE"
  }
  ```
- Response:
  ```json
  {
    "status": "success",
    "deposits": [...],
    "orders": [...],
    "timestamp": "ISO_TIMESTAMP"
  }
  ```