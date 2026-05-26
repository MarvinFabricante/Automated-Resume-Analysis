# Schemas Directory

This directory contains Pydantic models (often referred to as Data Transfer Objects or DTOs).

**Purpose:**
- Define the exact shape of data expected from incoming API requests.
- Define the shape of data sent out in API responses.
- Automatically validate incoming JSON payloads (types, constraints, required fields).
- Provide serialization and deserialization between raw JSON and Python dictionaries/objects.

These schemas ensure that invalid data never reaches the controllers or services.
