#!/usr/bin/env python3
"""
send_order_reminders.py
Script to query GraphQL endpoint for pending orders and log reminders.
"""

import sys
import asyncio
from datetime import datetime, timedelta
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql"

async def main():
    # Calculate cutoff date (7 days ago)
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    # Define GraphQL query
    query = gql("""
        query GetRecentOrders($cutoff: Date!) {
            orders(orderDate_Gte: $cutoff) {
                id
                customer {
                    email
                }
            }
        }
    """)

    # Transport and client
    transport = AIOHTTPTransport(url=GRAPHQL_URL)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Run query
    try:
        result = await client.execute_async(query, variable_values={"cutoff": cutoff_date})
        orders = result.get("orders", [])
    except Exception as e:
        print(f"Error querying GraphQL: {e}", file=sys.stderr)
        sys.exit(1)

    # Log reminders
    with open("/tmp/order_reminders_log.txt", "a") as log:
        for order in orders:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"{timestamp} - Reminder for Order {order['id']} to {order['customer']['email']}\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    asyncio.run(main())
