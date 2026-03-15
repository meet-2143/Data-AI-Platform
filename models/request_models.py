from pydantic import BaseModel, Field, field_validator
from typing import Optional, List,Dict, Any,Annotated
from config.settings import DEFAULT_MODEL_ID


# For charts and session management
class S3Config(BaseModel):
    bucket_name: Annotated[str , Field(description="S3 Bucket Name is required")]
    region: Annotated[str,Field(description="S3 Bucket Region is required")]

# Mcp config
class MCPConfig(BaseModel):
    mcp_url:Annotated[str,Field(description="MCP URL is required")]
    mcp_type: Annotated[str , Field(description="Type of MCP server",examples=['streamable_http','sse','stdio'])]

# Agent config
class AgentConfig(BaseModel):
    model_id: Annotated[str,Field(default=DEFAULT_MODEL_ID, description="Model ID used by the agent")]
    instructions: Annotated[str, Field(description="Agent-specific instructions",default='you are helpful assistant')]
    temperature: Annotated[Optional[float],Field(default=None, ge=0, le=1.5, description="Temperature setting for the model")]
    top_p: Annotated[Optional[float],Field(default=None, ge=0,le=1.0, description="Top-p value for sampling")]
    max_tokens: Annotated[Optional[int], Field(default=None, description="Max tokens to generate (0 means no limit)")]
    thinking_max_tokens:Annotated[int,Field(default=8000, description="Max tokens for thinking step")]
    mcp_config: Annotated[Optional[List[MCPConfig]],Field(default_factory=list)]

    @field_validator("thinking_max_tokens")
    def cap_thinking_max_tokens(cls, v):
        if v > 10000:
            return 8000
        return v


class AgentConfigBlock(BaseModel):
    main: Annotated[AgentConfig, Field(description="Main agent configuration")]
    

# conversation manager
class S3ConversationManagerConfig(BaseModel):
    sliding_window_size: Optional[int] = Field(default=20,description="Maximum number of recent messages to keep")
    prefix: Optional[str] = Field(default="testing-default/", description="Optional key prefix for S3 objects")


# knowledge Base
class KnowledgeBaseDetail(BaseModel):
    id: str = Field(description="Unique ID of the knowledge base")
    description: str= Field(description="Detailed description of the knowledge base")

# Main
class InvokeStrandsAgentBodyDetails(BaseModel):
    prompt:Annotated[str,Field(description='user query/ user question is required',examples=['hi','hello','how can you help me today'])]
    enable_thinking: Annotated[bool,Field(default=False,description='True if user want thinking/reaasoning , False if user want final response only')]
    session_id: Annotated[str,Field(description="Thread ID is required and it must be unique")]
    visual_output: Annotated[bool,Field(default=False,description="Flag to enable visual architecture")]
    agent_config: Annotated[AgentConfigBlock,Field(description='Agent config for calling bedrock api')]
    kb_details: Annotated[Optional[List[KnowledgeBaseDetail]] , Field(default_factory=list, description="List of knowledge base entries with ID and description")]
    s3: Annotated[S3Config, Field(description="S3 configuration is required for session and graph")]
    s3_conversation_config: Annotated[S3ConversationManagerConfig , Field(default_factory=S3ConversationManagerConfig,description="S3 Conversation Manager configuration")]
    agent_state: Annotated[Dict[str, Any] , Field(default_factory=dict,description="Initial agent state stored as key-value dictionary")]
    enable_tools_reasoning:Annotated [bool,Field(default=True)]