from strands import tool
import boto3

def make_kb_tool(kb_id, KB_description):
    
    client = boto3.client('bedrock-agent-runtime')
   
    tool_name = f"knowledgebase_query_{kb_id}"
    
    @tool(name=tool_name, description=KB_description)
    def kb_query(prompt: str) -> str:
        
        try:
            response = client.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={"text": prompt},
                retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 2}}
            )
            results = response.get("retrievalResults", [])
            formatted = "\n\n".join(
                r.get("content", {}).get("text", "No content") for r in results
            )
           
            return formatted or "No relevant information found."
        except Exception as e:
            return f"Retrieval error for {kb_id}.tool: {e}"
     
    
    return kb_query




