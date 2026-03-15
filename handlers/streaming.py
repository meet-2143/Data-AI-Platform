import json
from services.agent_service import create_agent
from main_tools import visuals
from main_tools.knowledgebase_tools import make_kb_tool
from strands.tools.mcp import MCPClient
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
import asyncio
from models.request_models import InvokeStrandsAgentBodyDetails
from services.agent_service import create_bedrock_model, create_conversation_manager

async def create_agent_stream(body:InvokeStrandsAgentBodyDetails):
        
         # Extract request parameters
        prompt = body.prompt.strip()
    
        prompt = prompt[:2000]
    
        #extracting enable thinking  true or false  
        enable_thinking = body.enable_thinking 

        #extracting visual output true or false
        enable_visual_output = body.visual_output

        #extracting threadID/ sessionId for S3 session manager 
        thread_id = body.session_id

        #Agent cofig for model parameter like model id temprature,max token etc.. 
        agent_config = body.agent_config
        base_agent_configs = agent_config.main

        #S3 config for visual output storage and history/session managment 
        s3_configs = body.s3
        
        #Agent instructions 
        agent_instructions = base_agent_configs.instructions

        #Agent state( things required to pass from main to tools in a key value pair)
        agent_state=body.agent_state
        
        #Enable tools reasoning True or False(which will be passsed in agent state asnd accuired in tools)
        enable_tools_reasoning=body.enable_tools_reasoning

        #Kb details 
        kb_details=body.kb_details

        #Mcp config 
        mcp_config=base_agent_configs.mcp_config

        #logic for enable tools reasoning(if enable thinking is False then by default tools reasoning is false)
        if not body.enable_thinking:
            enable_tools_reasoning=False

        

        # S3 Session managment dict 
        s3_history_manager ={
            "bucket_name":body.s3.bucket_name,
            "prefix":body.s3_conversation_config.prefix,
            "region": body.s3.region
        }
      

        #Conversation manager (Silding Window)
        s3_conversation_manager_config = body.s3_conversation_config.sliding_window_size

        # Create model with optional thinking capabilities
        bedrock_model = create_bedrock_model(
            config=base_agent_configs,
            enable_thinking=enable_thinking
        )
      
        # New updated  Create conversation manager
        conversation_manager = create_conversation_manager(s3_conversation_manager_config)
        
        
        
        #initializing  main tools 
        tools =[]
        mcp_client = None
        agent = None
    

        #MCP tools loading if provided
        if mcp_config is not None:
            for mcp_config in mcp_config:
                try:

                    if mcp_config.mcp_type == "sse":
                        mcp_client = MCPClient(lambda: sse_client(mcp_config.mcp_url))
                    elif mcp_config.mcp_type == "streamable_http":
                        mcp_client = MCPClient(lambda: streamablehttp_client(mcp_config.mcp_url))

                    await asyncio.get_event_loop().run_in_executor(
                        None, mcp_client.__enter__
                    )
                    mcp_client_success = True
                
                    # Get tools from MCP server
                    mcp_tools = await asyncio.get_event_loop().run_in_executor(
                        None, mcp_client.list_tools_sync
                    )
                
                    print(f"Retrieved {len(mcp_tools)} MCP tools\n")

                    

                    # Extract tool names for telemetry
                    mcp_tool_names = []
                    for mcp_tool in mcp_tools:
                        mcp_tool_name = getattr(mcp_tool, 'name', None) or getattr(mcp_tool, 'tool_name', None) or str(mcp_tool)
                        mcp_tool_names.append(mcp_tool_name)
                    
                    tools = tools + mcp_tools

                except Exception as e:
                    print(f"Error creating MCP client: {e}\n")

        
        # adding visual ouput tool  
        if enable_visual_output and s3_configs and s3_configs.bucket_name and s3_configs.region:
            
            tools = tools + [visuals]
        
        
        #adding KB tool
        if kb_details is not None:
            
            dynamic_KB_tools = [make_kb_tool(info.id, info.description) for info in kb_details]
            
            KB_tools_name = [f"knowledgebase_query_{info.id}" for info in kb_details]    
            
            print(f"Added {len(KB_tools_name)} tools for the Knowledge base query\n")   
            
            tools= tools + dynamic_KB_tools
        
        #Creating  Main agent 
        agent = create_agent(agent_instructions=agent_instructions,conversation_manager=conversation_manager,
                             s3_session_manager_config=s3_history_manager,model=bedrock_model,
                             thread_id=thread_id,tools=tools)
        
    

        #deleting agent state visual output for every new request to avoid yielding image url in every request

        is_visual = agent.state.get("visual_output")
        if is_visual is not None :
               print("deleting existing image url in state to generate new one")
               agent.state.delete("visual_output")
       # agent state
        agent.state.set("agent_state", agent_state)
        agent.state.set("enable_tools_reasoning", enable_tools_reasoning)
        agent.state.set("s3_bucket_region",s3_configs.region)
        agent.state.set("s3_bucket_name",s3_configs.bucket_name)
       
        print(f"\n agent state values : {agent.state.get("agent_state")}\n")
        print("enable tools reasoning : ", agent.state.get("enable_tools_reasoning"))

       
        
      
        #event metrics 
        event_metrics={
            "inputTokens": 0,
            "outputTokens": 0,
            "totalTokens": 0,
            "cacheReadInputTokens": 0,
            "cacheWriteInputTokens": 0
        }
        #final response and final reasoning initilization
        final_response = None
        final_reasoning =""
        tool_metric={}

        # agent call
        async for event in agent.stream_async(prompt=prompt):
            

            if "reasoningText" in event and enable_thinking:
                response_data = {
                                "type": "stream_chunk",
                                "data": event["reasoningText"],
                                "reasoning_complete": False
                            }
                yield f"data: {json.dumps(response_data)}\n\n"
                final_reasoning=final_reasoning+event["reasoningText"]

            if "tool_stream_event" in event and "final_response_end_stop" not in event.get("tool_stream_event", {}).get("data") and enable_thinking:
                response= event.get("tool_stream_event", {}).get("data")
                
                response_data = {
                                "type": "stream_chunk",
                                "data": response,
                                "reasoning_complete": False
                            }
                yield f"data: {json.dumps(response_data)}\n\n"
                final_reasoning=final_reasoning+response
            
            if "data" in event :
                response_data = {
                                "type": "stream_chunk",
                                "data": event["data"],
                                "reasoning_complete": True
                            }
                yield f"data: {json.dumps(response_data)}\n\n"

            if "result" in event:

                tool_event=event['result'].metrics.tool_metrics
                for i in tool_event:
                    tool_metric[i]= tool_event[i].call_count
                
                # Print tool name logs - which tools were used
                if tool_metric:
                    print(f"\n[TOOL USAGE] Tools used in this request:")
                    for tool_name, call_count in tool_metric.items():
                        print(f"  - {tool_name}: {call_count} time(s)")
                    print()
    
                final_response = event["result"]     

            #Metrics for input and output tokens
            if "event" in event and "metadata" in event["event"]:
                usage = event["event"]["metadata"].get("usage", {}) or {}
                
                event_metrics = {
                    "inputTokens": usage.get("inputTokens", 0),
                    "outputTokens": usage.get("outputTokens", 0),
                    "totalTokens": usage.get("totalTokens", 0),
                    "cacheReadInputTokens": usage.get("cacheReadInputTokens", 0),
                    "cacheWriteInputTokens": usage.get("cacheWriteInputTokens", 0)
                    }
              
        
        visual_output = agent.state.get("visual_output")
        
        if visual_output is not None and len(visual_output)!=0:

            for i in visual_output:
                print("Received image url:",i)
                response_data = {
                                "type": "image",
                                "data": i,
                                "reasoning_complete": True,
                            }
                print("Response data:",response_data)
                yield f"data: {json.dumps(response_data)}\n\n"
                
        # Extract custom_fields from agent_state - this is where tools set response state fields
        # custom_fields is a dict that tools can populate with fields like dbUpdated
        agent_response_state = {}  # Start with empty dict
        try:
            # Get agent_state dict from agent (may be None)
            current_agent_state = agent.state.get("agent_state")
            if current_agent_state is not None and isinstance(current_agent_state, dict):
                # Extract custom_fields from agent_state
                custom_fields = current_agent_state.get("custom_fields")
                if custom_fields is not None and isinstance(custom_fields, dict):
                    # Copy all fields from custom_fields to agent_response_state
                    agent_response_state = custom_fields.copy()
        except Exception as e:
            print(f"Error reading custom_fields from agent state: {e}")

        response_data = {
                        "type": "final_summary",
                        "reasoning": str(final_reasoning),
                        "final_output":str(final_response),
                        "reasoning_complete": True,
                        "complete": True,
                        "event_metrics": event_metrics,
                        'tool_metric':tool_metric,
                        "agent_response_state": agent_response_state
                       }
        
        yield f"data: {json.dumps(response_data)}\n\n"