# Repositories Directory

This directory implements the Repository Pattern to abstract data access.

**Purpose:**
- Centralize all database interactions (SQLAlchemy ORM queries, raw SQL).
- Isolate the application's business logic (`services/`) from the underlying database technology.
- Provide a clear API for CRUD (Create, Read, Update, Delete) operations.

Whenever a service needs to fetch or save data to the database, it calls the corresponding methods in a repository class instead of interacting with the database session directly.
