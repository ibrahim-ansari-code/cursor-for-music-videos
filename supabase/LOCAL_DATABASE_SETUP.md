# Local Database Setup Guide (Supabase)

This guide provides instructions for setting up and running the local PostgreSQL database using the Supabase development environment. This setup is managed via Docker and the Supabase CLI, ensuring a consistent and isolated database environment that mirrors our production schema.

## Prerequisites

1.  **Docker Desktop**: Ensure Docker Desktop is installed and running on your machine. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).
2.  **Supabase CLI**: The Supabase Command Line Interface is required to manage the local development environment. Install it globally via npm:
    ```bash
    npm install -g supabase
    ```

---

## Initial Setup for New Developers

This is a one-time setup process for any developer cloning the project for the first time.

1.  **Clone the Repository**:

    ```bash
    git clone https://github.com/Brikli-Property-Management/Brikli-V2
    cd Brikli-V2
    ```

2.  **Start Supabase Services**:
    This is the core command. It initializes and starts all necessary Docker containers (Postgres, GoTrue Auth, Realtime, Storage, etc.).

    ```bash
    supabase start
    ```

    **What this command does automatically:**

    - Pulls the required Docker images.
    - Starts the local Supabase stack.
    - **Applies all migrations** located in the `supabase/migrations/` directory. This is crucial as it sets up your local database schema to match the one defined in the repository, including the baseline sync from production.

3.  **Verify the Setup**:
    After the command finishes, you will see a list of local URLs and keys. You can also verify that all services are running correctly at any time:
    ```bash
    supabase status
    ```
    You should see all services running with `healthy` status.

---

## Connecting to Your Local Database

Once the services are running, you can connect to your local PostgreSQL instance using any standard database client (like DBeaver, TablePlus, or your IDE's database tools).

- **Connection String**: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Host**: `127.0.0.1`
- **Port**: `54322`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `postgres`

You can also access the Supabase Studio dashboard locally at **http://127.0.0.1:54323**.

---

## Daily Workflow Commands

Here are the common commands you'll use in your day-to-day development.

- **Stop Services**: To gracefully shut down the local Supabase stack:

  ```bash
  supabase stop
  ```

- **Stop and Discard Data**: If you want to stop the services and discard all data in your local database (useful for a clean slate):

  ```bash
  supabase stop --no-backup
  ```

- **Reset the Database**: This will destroy all data in your local database and re-apply all migrations from scratch. This is useful if your local schema gets out of sync or corrupted.
  ```bash
  supabase db reset
  ```

---

## Making Schema Changes

This project uses a **dual migration system** involving both **Alembic** and **Supabase migrations**. Understanding when to use each system is crucial for maintaining database consistency.

### When to Use Alembic Migrations

Use Alembic when you're making changes to **SQLModel classes** in the `Backend/models/` directory:

- **Adding/removing model classes** (e.g., creating a new `Vendor` model)
- **Adding/removing fields** to existing models (e.g., adding `phone_number` to `User`)
- **Changing field types or constraints** (e.g., making a field nullable, changing max length)
- **Adding/removing indexes** defined in SQLModel classes
- **Modifying relationships** between models (e.g., adding a ForeignKey)

**Examples of SQLModel changes:**
```python
# Adding a new field to an existing model
class Property(SQLModel, table=True):
    # ... existing fields ...
    square_footage: int | None = None  # ← Use Alembic

# Creating a new model
class Vendor(SQLModel, table=True):  # ← Use Alembic
    id: int = Field(primary_key=True)
    name: str
    # ...
```

### When to Use Supabase Migrations

Use Supabase migrations for **database-specific features** that aren't represented in SQLModel:

- **Row Level Security (RLS) policies** (e.g., ensuring users only see their own data)
- **Database functions and triggers** (e.g., auto-updating timestamps)
- **Custom SQL types or enums** not supported by SQLModel
- **Database views or materialized views**
- **Complex constraints** that can't be expressed in SQLModel
- **Performance optimizations** like specialized indexes (GIN, GiST, etc.)
- **Direct SQL operations** for data migrations or cleanups

**Examples of database-specific changes:**
```sql
-- RLS policy (use Supabase migration)
CREATE POLICY "Users can only view their own properties"
ON properties FOR SELECT
USING (user_id = auth.uid());

-- Custom function (use Supabase migration)
CREATE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Specialized index for text search (use Supabase migration)
CREATE INDEX idx_expenses_description_trgm 
ON expenses USING gin (description gin_trgm_ops);
```

### Quick Decision Guide

Ask yourself these questions:

1. **Am I modifying a Python file in `Backend/models/`?** → Use **Alembic**
2. **Am I writing raw SQL or using Supabase Studio?** → Use **Supabase migrations**
3. **Is this about security policies or database functions?** → Use **Supabase migrations**
4. **Am I changing table structure based on SQLModel classes?** → Use **Alembic**

For a detailed breakdown of the migration workflows and specific commands for each scenario, please refer to:

➡️ **[CLAUDE.md](../CLAUDE.md#migration-strategy)**

This ensures we have a single source of truth for our migration process.