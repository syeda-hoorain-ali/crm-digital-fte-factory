# Database Configuration

The MCP server supports different database configurations based on the environment:

## Environment-Specific Behavior

### Testing (`ENVIRONMENT=testing`)
- Uses SQLite database: `sqlite:///./test.db`
- Ideal for isolated test runs
- Separate from development data

### Development (`ENVIRONMENT=development`)
- If `NEON_DATABASE_URL` environment variable is set: uses that PostgreSQL connection
- Otherwise: falls back to SQLite database: `sqlite:///./dev.db`
- Perfect for local development and Neon PostgreSQL integration

### Production (`ENVIRONMENT=production`)
- Requires a production-ready database (PostgreSQL, MySQL, etc.)
- **Forbids** SQLite usage - will raise an error if SQLite URL is detected
- Ensures production systems use appropriate database infrastructure

## Setup Examples

### For Local Development with SQLite:
```bash
ENVIRONMENT=development
# Uses dev.db by default
```

### For Development with Neon PostgreSQL:
```bash
ENVIRONMENT=development
NEON_DATABASE_URL=postgresql://username:password@ep-xxxxxx.us-east-1.aws.neon.tech/dbname?sslmode=require
```

### For Testing:
```bash
ENVIRONMENT=testing
# Automatically uses test.db
```

### For Production:
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://prod-username:prod-password@prod-host/dbname
# SQLite URLs like sqlite:/// will cause the application to fail at startup
```