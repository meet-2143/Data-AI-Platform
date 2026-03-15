# new s3 version enabled session manager
from strands import Agent
from strands.models import BedrockModel
from config.settings import AWS_PROFILE, DEFAULT_MODEL_ID
from models.request_models import  AgentConfig
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.s3_session_manager import S3SessionManager
from strands.models import BedrockModel


def create_agent(thread_id: str, model:BedrockModel, conversation_manager,s3_session_manager_config: dict,agent_instructions:str,tools:list) -> Agent:
    """Restore agent state from S3 with improved error handling"""
    try:
        print(f"thread_id: {thread_id},s3 bucket name: where the history will get stored:- {s3_session_manager_config.get("bucket_name")}")
        # Initialize S3 session manager with provided bucket name
        session_manager = S3SessionManager(
        session_id=thread_id,
        bucket=s3_session_manager_config.get("bucket_name"),
        prefix=s3_session_manager_config.get("prefix"),
        region_name=s3_session_manager_config.get("region")
        )


        restored_agent = Agent(
            model=model,
            session_manager=session_manager,
            tools=tools,
            conversation_manager=conversation_manager,
            callback_handler=None,
            system_prompt=agent_instructions,
            load_tools_from_directory=True
        )
        
        print(f"Agent created successfully for thread: {thread_id}")
        return restored_agent
        
    except Exception as e:
        print(e)
        
 

def create_bedrock_model(config: AgentConfig, enable_thinking: bool = False):
    """Create BedrockModel with optional thinking capabilities"""
    model_config = {
        "model_id":config.model_id or DEFAULT_MODEL_ID
    }


    if config.temperature is not None:
        model_config["temperature"] = config.temperature

    if config.top_p is not None and "temperature" not in model_config:
        model_config["top_p"] = config.top_p

    # Only add max_tokens if it's a valid positive integer (Bedrock requires >= 1)
    # If max_tokens is 0 or None, omit it to let Bedrock use its default behavior
    if config.max_tokens is not None and config.max_tokens > 0:
        model_config["max_tokens"] = config.max_tokens

    
    if enable_thinking and (config.model_id!='openai.gpt-oss-120b-1:0' and config.model_id!='openai.gpt-oss-20b-1:0'):
        model_config["temperature"] = 1
        model_config.pop("top_p", None)
        model_config["additional_request_fields"] = {
            "thinking": {"type": "enabled", "budget_tokens": config.thinking_max_tokens}
        }
    if enable_thinking and config.model_id=='openai.gpt-oss-120b-1:0' or config.model_id=='openai.gpt-oss-20b-1:0':
        model_config["temperature"]=1 
    
    print(f"model config passed to agent :- {model_config}")
    return BedrockModel(**model_config)





def create_conversation_manager(sliding_window_size: int) -> SlidingWindowConversationManager:
    """Create conversation manager with sliding window config"""
    print("this is window size",sliding_window_size)
    conversation_manager = SlidingWindowConversationManager(
        window_size=sliding_window_size,
        should_truncate_results=False
    )
    return conversation_manager






