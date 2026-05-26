# Services Directory

This directory contains the core business logic of the application.

**Purpose:**
- House the complex rules, workflows, and operations of the application.
- Act as a bridge between the `controllers/` (which handle HTTP requests) and the `repositories/` (which handle database operations).
- Coordinate multiple data models, external APIs (like Twilio, LLMs), and background tasks.

By isolating business logic into services, the codebase becomes highly reusable and much easier to unit test.
