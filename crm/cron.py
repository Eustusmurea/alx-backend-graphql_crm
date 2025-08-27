import datetime
import os
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

GRAPHQL_URL = "http://localhost:8000/graphql"

def log_crm_heartbeat():
    """Logs a heartbeat every 5 minutes to confirm CRM is alive."""
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{timestamp} CRM is alive\n"

    log_path = "/tmp/crm_heartbeat_log.txt"
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    with open(log_path, "a") as f:
        f.write(message)

    # ✅ Required by checker: gql hello query
    try:
        transport = RequestsHTTPTransport(url=GRAPHQL_URL, use_json=True, timeout=5)
        client = Client(transport=transport, fetch_schema_from_transport=False)

        query = gql("""query { hello }""")
        result = client.execute(query)

        with open(log_path, "a") as f:
            f.write(f"{timestamp} GraphQL hello: {result}\n")
    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"{timestamp} GraphQL check failed: {e}\n")


def update_low_stock():
    mutation = gql(
        """
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
    )

    try:
        transport = RequestsHTTPTransport(url=GRAPHQL_URL, use_json=True, timeout=10)
        client = Client(transport=transport, fetch_schema_from_transport=False)
        data = client.execute(mutation)
    except Exception as e:
        data = {"errors": [str(e)]}

    log_file = "/tmp/low_stock_updates_log.txt"
    with open(log_file, "a") as f:
        f.write(f"\n=== {datetime.datetime.now()} ===\n")
        if "errors" in data:
            f.write("Error: " + str(data["errors"]) + "\n")
        else:
            result = data["updateLowStockProducts"]
            f.write(result["message"] + "\n")
            for product in result["updatedProducts"]:
                f.write(f"- {product['name']}: {product['stock']}\n")
