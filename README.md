# Strands Project

This project is a FastAPI-based backend service designed to invoke the Strands Agent, leveraging AWS services and providing streaming responses for AI-driven tasks. The codebase is modular, with clear separation of concerns for configuration, request handling, service integration, and utility functions.

## Features
- **FastAPI** REST API with CORS support
- Streaming and non-streaming agent responses
- Integration with AWS (Boto3, S3, Bedrock)
- Modular service, handler, and utility structure
- Error handling and logging utilities

## Project Structure
```
main.py                  # FastAPI app entry point and endpoint definitions
config/
  settings.py            # Configuration settings (e.g., AWS profile, model ID)
handlers/
  separator.py           # Output separator logic
  streaming.py           # Streaming response logic for agent
models/
  request_models.py      # Pydantic models for request validation
services/
  agent_service.py       # Agent/model creation and management
  dynamodb_service.py    # (Presumed) DynamoDB integration
  s3_service.py          # S3 schema reference utilities
utils/
  logging_utils.py       # Logging and error utilities
```

## Setup
1. **Clone the repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure AWS credentials**:
   - Set up your AWS profile as referenced in `config/settings.py` (e.g., `AWS_PROFILE`)
4. **Run the server**:
   ```bash
   uvicorn main:app --reload
   ```

## API Endpoint
### `POST /invoke_strands_agent/`
Invokes the Strands Agent with the provided prompt and configuration.

**Request Body (JSON):**
- `prompt` (str): The user prompt (required)
- `mcp_url` (str): MCP server URL
- `s3_bucket_name` (str): S3 bucket for schema reference (optional)
- `agent_instructions` (str): Instructions for the agent (supports formatting with schema reference)
- `session_id` (str): Session/thread identifier
- `enable_thinking` (bool): Enables streaming/thinking mode

**Response:**
- Streaming or plain text response from the agent
- Error details in JSON on failure

## Notes
- Ensure your AWS credentials and permissions are correctly configured.
- The agent supports both streaming (SSE) and non-streaming responses based on the `enable_thinking` flag.
- Extend or modify handlers/services as needed for your use case.

## License
[MIT](LICENSE)
