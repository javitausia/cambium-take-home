#!/bin/bash

# Start PostgreSQL in the background
su - postgres -c "pg_ctl start -D \$PGDATA"

# Wait for PostgreSQL to start up properly
until pg_isready -U $POSTGRES_USER -d $POSTGRES_DB; do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

# Run the SQL script to create extensions
psql -U $POSTGRES_USER -d $POSTGRES_DB -f /docker-entrypoint-initdb.d/init_db.sql

# Keep the container running
tail -f /dev/null