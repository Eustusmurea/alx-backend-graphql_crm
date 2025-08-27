#!/bin/bash

PROJECT_DIR="/home/eustus/Desktop/ALX/alx_backend_graphql_crm"
VENV_DIR="/home/eustus/Desktop/ALX/graph"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run cleanup via Django shell
deleted_count=$(python "$PROJECT_DIR/manage.py" shell -c "
from datetime import timedelta
from django.utils import timezone
from crm.models import Customer

cutoff = timezone.now() - timedelta(days=365)
deleted, _ = Customer.objects.filter(orders__isnull=True, created__lt=cutoff).delete()
print(deleted)
")

# Log results with timestamp
echo \"\$(date '+%Y-%m-%d %H:%M:%S') - Deleted \$deleted_count inactive customers\" >> /tmp/customer_cleanup_log.txt
