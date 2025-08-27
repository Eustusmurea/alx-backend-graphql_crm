import requests
from datetime import datetime
from celery import shared_task

GRAPHQL_URL = "http://127.0.0.1:8000/graphql/"

@shared_task
def generate_crm_report():
    query = """
    {
        allCustomers {
            totalCount
        }
        allOrders {
            totalCount
        }
        allOrders {
            edges {
                node {
                    totalAmount
                }
            }
        }
    }
    """

    response = requests.post(GRAPHQL_URL, json={"query": query})
    data = response.json()

    log_file = "/tmp/crm_report_log.txt"
    with open(log_file, "a") as f:
        f.write(f"\n=== {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")

        if "errors" in data:
            f.write("Error: " + str(data["errors"]) + "\n")
        else:
            customers = data["data"]["allCustomers"]["totalCount"]
            orders = data["data"]["allOrders"]["totalCount"]
            revenue = sum([
                float(edge["node"]["totalAmount"])
                for edge in data["data"]["allOrders"]["edges"]
            ])

            f.write(f"Report: {customers} customers, {orders} orders, {revenue} revenue\n")
