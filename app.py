from flask import Flask, request, jsonify
import snowflake.connector
import os
from dotenv import load_dotenv
from datetime import datetime
from decimal import Decimal

# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route("/")
def home():
    return "Flask server is running!"

@app.route("/health")
def health():
    return "OK"

@app.route("/api/data", methods=["POST"])
def api_data():
    try:
        data = request.get_json()
        customer_id = data.get("customer_id")

        if not customer_id:
            return jsonify({"error": "Customer ID is required"}), 400

        # Connect to Snowflake using external OAuth
        conn = snowflake.connector.connect(
            user=os.environ['SNOWFLAKE_USER'],
            account=os.environ['SNOWFLAKE_ACCOUNT'],
            warehouse=os.environ['SNOWFLAKE_WAREHOUSE'],
            database=os.environ['SNOWFLAKE_DATABASE'],
            schema=os.environ['SNOWFLAKE_SCHEMA'],
            authenticator='externalbrowser',
            role=os.environ.get('SNOWFLAKE_ROLE', 'THORVATH'),
            token_cache=os.path.expanduser("~/.snowflake/token_cache.json")
)

        cursor = conn.cursor()
        cursor.execute("USE WAREHOUSE ADHOC__XLARGE")

        def to_json_safe(val):
            if isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, Decimal):
                return float(val)
            return val

        # ----- DEPOSITS -----
        deposits_query = f"""
        SELECT
            date_trunc('day', t.created_at) AS the_date,
            balance_authority_token AS unit_token,
            CASE 
                WHEN RLIKE(dde.description, '.*doordash.*', 'i') THEN 'DOORDASH' 
                WHEN RLIKE(dde.description, '.*uber.*', 'i') THEN 'UBER_EATS' 
            END AS Platform,
            SUM(dde.amount_cents)/100 AS original_deposit_amount,
            SUM(br.amount_cents)/100 AS adjusted_amount
        FROM (
            SELECT * 
            FROM bankc.raw_oltp.transactions
            WHERE transaction_type = 'ADJUSTED_DIRECT_DEPOSIT_IN'
              AND balance_authority_token = '{customer_id}'
              AND created_at > '2023-02-10'
        ) t
        LEFT JOIN inflows.raw_oltp.direct_deposit_events dde
            ON t.transaction_id = dde.direct_deposit_token
           AND dde.state = 'SETTLED'
        LEFT JOIN bankc.raw_oltp.balance_reservations br
            ON br.transaction_id = t.transaction_id
           AND br.balance_reservation_id = t.transaction_id
           AND br.created_at > '2023-02-10'
        GROUP BY 1, 2, 3
        ORDER BY 1 ASC, 2
        """
        cursor.execute(deposits_query)
        deposits = cursor.fetchall()
        deposits_data = [
            [to_json_safe(v) for v in row] for row in deposits
        ]

        # ----- ORDERS -----
        orders_query = f"""
        SELECT 
            date_trunc('day', created_at) AS the_date,
            balance_owner_id,
            source_type,
            SUM(amount_cents)/100 AS total_volume,
            SUM(prefunded_amount_cents)/100 AS total_prefunded,
            SUM(CASE WHEN state = 'CANCELLED' THEN amount_cents ELSE 0 END)/100 AS cancelled_amount,
            SUM(CASE WHEN state = 'PREFUNDED' THEN amount_cents ELSE 0 END)/100 AS acted_on_amount
        FROM inflows.raw_oltp.attributed_funds
        WHERE balance_owner_id = '{customer_id}'
          AND source_type IN ('DOORDASH_ORDER', 'UBER_EATS_ORDER')
        GROUP BY 1, 2, 3
        ORDER BY 1 DESC
        """
        cursor.execute(orders_query)
        orders = cursor.fetchall()
        orders_data = [
            [to_json_safe(v) for v in row] for row in orders
        ]

        cursor.close()
        conn.close()

        return jsonify({
            'status': 'success',
            'deposits': deposits_data,
            'orders': orders_data
        })

    except Exception as e:
        print("❌ Error:", str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Flask server...")
    app.run(debug=True, port=8080)
