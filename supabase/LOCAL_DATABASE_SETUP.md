# Local Database Setup Guide (Supabase)

This guide provides instructions for setting up and running the local PostgreSQL database using the Supabase development environment. This setup is managed via Docker and the Supabase CLI, ensuring a consistent and isolated database environment that mirrors our production schema.

## Prerequisites

1. **Docker Desktop**: Ensure Docker Desktop is installed and running on your machine. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).
2. **Supabase CLI**: The Supabase Command Line Interface is required to manage the local development environment. Install it globally via npm:

    ```bash
    npm install -g supabase
    ```

---

## Initial Setup for New Developers

This is a one-time setup process for any developer cloning the project for the first time.

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/Brikli-Property-Management/Brikli-V2
    cd Brikli-V2
    ```

2. **Start Supabase Services**:
    This is the core command. It initializes and starts all necessary Docker containers (Postgres, GoTrue Auth, Realtime, Storage, etc.).

    ```bash
    supabase start
    ```

    **What this command does automatically:**

    - Pulls the required Docker images.
    - Starts the local Supabase stack.
    - **Applies all migrations** located in the `supabase/migrations/` directory. This is crucial as it sets up your local database schema to match the one defined in the repository, including the baseline sync from production.

3. **Load Test Data** (Recommended):
    After the initial setup, populate your database with comprehensive test data:

    ```bash
    supabase db reset --local
    ```

    This will apply the schema migrations and load the seed data from `supabase/seed.sql`, giving you a rich dataset for development and testing.

4. **Verify the Setup**:
    After the command finishes, you will see a list of local URLs and keys. You can also verify that all services are running correctly at any time:

    ```bash
    supabase status
    ```

    You should see all services running with `healthy` status.

---

## Comprehensive Test Data

The local database comes with extensive seed data that covers all major use cases:

### **User Management (9 users)**

- **Main test user**: `test.user@brikli.dev` (matches auth system)
- **Landlords**: John Smith, Sarah Johnson, Mike Williams  
- **Tenants**: Alice Brown, David Davis, Emma Wilson (with user accounts)
- **Additional tenants**: Robert, Lisa, James, Maria, Kevin (without user accounts)
- **Staff**: Bob Maintenance
- **Admin**: Admin User

### **Property Portfolio (8 properties, 18 units)**

- **Maple Apartments** (Toronto): 24-unit building with 5 sample units
- **Downtown Condos** (Toronto): Luxury condominiums  
- **Student Housing Complex** (Toronto): University-area housing
- **Oakville Family Homes** (Oakville): Townhomes
- **Business Plaza** (Mississauga): Commercial spaces
- **Riverside Apartments** (Hamilton): Scenic apartment complex
- **Industrial Warehouse** (Burlington): Large warehouse facility
- **Suburban Duplex** (Brampton): Well-maintained duplex

### **Financial Data**

- **10 Payments**: Recent, historical, late, and overdue payments with various methods
- **7 Invoices**: Different statuses (Paid, Overdue, Partial, Pending)
- **10 Expenses**: Property management costs with HST tax details
- **8 Active Leases**: Current tenant agreements with different terms
- **2 Historical Leases**: Expired and terminated leases

### **Operational Data**

- **7 Maintenance Requests**: Various priorities and statuses (Completed, In Progress, Scheduled, Pending)
- **3 QuickBooks Integrations**: Different connection states (Connected, Disconnected, Error)
- **3 AI Agent Threads**: Sample conversation history for AI features
- **8 Tenant-Unit Links**: Current and historical occupancy tracking

---

## Connecting to Your Local Database

Once the services are running, you can connect to your local PostgreSQL instance using any standard database client (like DBeaver, TablePlus, or your IDE's database tools).

- **Connection String**: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- **Host**: `127.0.0.1`
- **Port**: `54322`
- **User**: `postgres`
- **Password**: `postgres`
- **Database**: `postgres`

You can also access the Supabase Studio dashboard locally at **<http://127.0.0.1:54323>**.

### **API Access**

The local Supabase API is available at:

- **API URL**: `http://127.0.0.1:54321`
- **Keys**: Available from `supabase status` command output
  
**Note**: API keys are generated automatically by Supabase for local development and can be viewed using `supabase status`.

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

- **Reset with Fresh Data**: This will destroy all data in your local database, re-apply all migrations, and reload the comprehensive seed data:

  ```bash
  supabase db reset --local
  ```

- **Reset Without Seed Data**: If you want a clean database without test data:

  ```bash
  # Temporarily disable seeding in supabase/config.toml
  # Set enabled = false under [db.seed]
  supabase db reset --local
  ```

- **Apply New Migrations Only**: If you want to apply new migrations without resetting all data:

  ```bash
  supabase migration up --local
  ```

---

## Development Tips

### **Testing with Realistic Data**

The seed data provides realistic scenarios for testing:

- **Multi-tenant testing**: Different landlords with their own properties
- **Payment scenarios**: Various payment methods, statuses, and timing
- **Maintenance workflows**: Requests at different stages
- **Financial reporting**: Historical data for month-over-month comparisons
- **User permissions**: Different user types and access levels

### **API Testing**

Use the seeded data for API testing:

```bash
# Test user authentication with seeded users
# Test property queries with realistic property data  
# Test payment processing with existing payment records
# Test maintenance request workflows
```

### **Database Queries**

Common queries for development:

```sql
-- Check all users and their types
SELECT email, first_name, last_name, user_type FROM users;

-- View property portfolio
SELECT name, address, city, property_type, status FROM properties;

-- Check recent payments
SELECT amount, payment_method, status, payment_date FROM payments 
ORDER BY payment_date DESC LIMIT 10;

-- View maintenance requests by priority
SELECT issue_title, priority, status, property_id, unit_id 
FROM maintenance_requests ORDER BY priority DESC;
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

**Alembic Workflow:**

```bash
# 1. Make changes to SQLModel classes in Backend/models/
# 2. Generate migration
cd Backend
poetry run alembic revision --autogenerate -m "Add square_footage to Property"
# 3. Review and edit the generated migration if needed
# 4. Apply to local database
poetry run alembic upgrade head
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

**Supabase Migration Workflow:**

```bash
# 1. Create new migration file
supabase migration new add_property_search_index
# 2. Edit the generated file in supabase/migrations/
# 3. Apply to local database
supabase migration up --local
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

---

## Configuration

⚠️ **CRITICAL SECURITY WARNING** ⚠️

The Supabase configuration in `supabase/config.toml` is **LOCAL DEVELOPMENT ONLY** and should **NEVER be deployed to production**.

### **Local Development Settings**

The following settings are enabled for local development:

- **Migrations**: `enabled = true` - Automatically applies schema changes
- **Seeding**: `enabled = true` - Loads test data from `supabase/seed.sql`
- **Auth**: Configured for local development with test users
- **Storage**: Local file storage for development

### **Production Deployment Risk**

**DO NOT deploy this configuration to production as it will:**

- ❌ Apply unintended schema migrations automatically
- ❌ Overwrite production data with test data
- ❌ Reset your production database

### **Environment-Specific Configuration**

For production deployments, ensure:

- `[db.migrations] enabled = false`
- `[db.seed] enabled = false`
- Use environment-specific configuration management

### **CRITICAL: Production Safety Rules**

⚠️ **PRIMARY RULE: Never link local development to production**

```bash
# ❌ NEVER DO THIS with production project ID
supabase link --project-ref YOUR_PROD_PROJECT_ID
```

⚠️ **If you must work with production (use CI/CD instead):**

```bash
# 1. Always check what you're linked to
supabase status

# 2. Use dry-run to preview changes
supabase db push --dry-run

# 3. NEVER use these commands on production
supabase db push         # ❌ Will apply local config to production  
supabase db reset        # ❌ Will destroy production data
```

**Production deployments should use:**

- 🏗️ **CI/CD pipelines** (GitHub Actions, not local commands)
- 🔒 **Separate environments** (dev, staging, prod projects)
- 📋 **Code reviews** for all migration changes

To modify seeding behavior for local development only, edit the `[db.seed]` section in `supabase/config.toml`.
