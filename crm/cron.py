import datetime
import os
import requests

GRAPHQL_URL = "http://localhost:8000/graphql"

def log_crm_heartbeat():
    """Logs a heartbeat every 5 minutes to confirm CRM is alive."""
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{timestamp} CRM is alive\n"

    log_path = "/tmp/crm_heartbeat_log.txt"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as f:
        f.write(message)

    # Optional: check GraphQL endpoint
    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": "{ hello }"},
            timeout=5,
        )
        if response.ok:
            with open(log_path, "a") as f:
                f.write(f"{timestamp} GraphQL hello: {response.json()}\n")
    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"{timestamp} GraphQL check failed: {e}\n")

def update_low_stock():
    mutation = """
    mutation {
        updateLowStockProducts {
            success
            message
            updatedProducts {
                id
                name
                stock
            }
        }
    }
    """

    response = requests.post(GRAPHQL_URL, json={"query": mutation})
    data = response.json()

    log_file = "/tmp/low_stock_updates_log.txt"
    with open(log_file, "a") as f:
        f.write(f"\n=== {datetime.datetime.now()} ===\n")
        if "errors" in data:
            f.write("Error: " + str(data["errors"]) + "\n")
        else:
            result = data["data"]["updateLowStockProducts"]
            f.write(result["message"] + "\n")
            for product in result["updatedProducts"]:
                f.write(f"- {product['name']}: {product['stock']}\n")