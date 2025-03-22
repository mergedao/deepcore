import json
import logging
from typing import Dict, List, Any, Optional

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.sse import SseServerTransport
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import Response

from agents.common.config import SETTINGS
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.models import MCPServer, MCPTool, MCPPrompt, MCPResource
from agents.services.tool_service import get_tool, get_tools_by_ids
from agents.utils.http_client import async_client
from agents.utils.session import get_async_session, get_async_session_ctx

logger = logging.getLogger(__name__)

async def create_mcp_server_from_tools(
    mcp_name: str,
    tool_ids: List[str],
    user: dict,
    session: AsyncSession,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create an MCP server from a list of tool IDs
    
    Args:
        mcp_name: MCP server name
        tool_ids: List of tool IDs to expose as MCP interface
        user: Current user information
        session: Database session
        description: Optional MCP service description
        
    Returns:
        Dictionary containing service information
    """
    try:
        # Check if the name is already in use in database
        existing_server = await session.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        if existing_server.scalar_one_or_none():
            raise CustomAgentException(
                ErrorCode.RESOURCE_ALREADY_EXISTS,
                f"MCP server with name '{mcp_name}' already exists"
            )
            
        # Create MCP server database record instead of in-memory instance
        mcp_server = MCPServer(
            name=mcp_name,
            description=description or f"MCP server for {len(tool_ids)} tools",
            tenant_id=user["tenant_id"]
        )
        session.add(mcp_server)
        await session.flush()  # Ensure ID is assigned
            
        # Create tool associations
        for tool_id in tool_ids:
            mcp_tool = MCPTool(
                mcp_server_id=mcp_server.id,
                tool_id=tool_id
            )
            session.add(mcp_tool)
        
        await session.commit()
            
        # No longer need to register handlers or store server instance in memory
        
        return {
            "mcp_name": mcp_name,
            "tool_count": len(tool_ids),
            "tool_ids": tool_ids,
            "url": f"{SETTINGS.API_BASE_URL}/mcp/{mcp_name}",
            "description": description or f"MCP server for {len(tool_ids)} tools"
        }
        
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error creating MCP server: {e}", exc_info=True)
        raise CustomAgentException(
            ErrorCode.API_CALL_ERROR,
            f"Failed to create MCP server: {str(e)}"
        )

async def _create_server_instance(mcp_name: str, user: dict) -> Server:
    """
    Dynamically create an MCP server instance for the given name
    
    Args:
        mcp_name: MCP server name
        user: User information for authorization
        
    Returns:
        Server instance configured with handlers
    """
    # Create a new server instance for this request
    server = Server(mcp_name)
    
    # Register tool list handler - now queries database directly
    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools by querying database"""
        logger.info(f"MCP server '{mcp_name}' received list_tools request")
        # Get tools from database
        mcp_tools = []
        async with get_async_session_ctx() as db_session:
            # Get MCP server with associated tools
            db_server = await db_session.execute(
                select(MCPServer)
                .options(selectinload(MCPServer.tools).selectinload(MCPTool.tool))
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                logger.warning(f"MCP server '{mcp_name}' not found")
                return []
            
            # Collect all tool IDs
            tool_ids = [str(mcp_tool.tool_id) for mcp_tool in server_obj.tools]
            
            # Batch retrieve tool objects
            tool_map = await get_tools_by_ids(tool_ids, user, db_session)
            
            # Create MCP tool format for each tool
            for mcp_tool in server_obj.tools:
                tool = tool_map.get(str(mcp_tool.tool_id))
                if not tool:
                    continue
                
                # Convert tool parameters to MCP input schema
                input_schema = _convert_parameters_to_schema(tool.parameters)
                
                mcp_tool = types.Tool(
                    name=tool.name,
                    description=tool.description or f"Tool {tool.name}",
                    inputSchema=input_schema
                )
                mcp_tools.append(mcp_tool)
        
        logger.info(f"MCP server '{mcp_name}' returned {len(mcp_tools)} tools")
        return mcp_tools
        
    # Register tool call handler
    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent | types.ImageContent]:
        """Handle tool execution request"""
        logger.info(f"MCP server '{mcp_name}' received tool call request: {name}")
        # Get tools from database
        async with get_async_session_ctx() as db_session:
            # Get MCP server with associated tools
            db_server = await db_session.execute(
                select(MCPServer)
                .options(selectinload(MCPServer.tools).selectinload(MCPTool.tool))
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                return [types.TextContent(type="text", text=f"MCP server not found: {mcp_name}")]
            
            # Collect all tool IDs
            tool_ids = [str(mcp_tool.tool_id) for mcp_tool in server_obj.tools]
            
            # Batch retrieve tool objects
            tool_map = await get_tools_by_ids(tool_ids, user, db_session)
            
            # Find matching tool
            matching_tool = None
            for mcp_tool in server_obj.tools:
                tool = tool_map.get(str(mcp_tool.tool_id))
                if tool and tool.name == name:
                    matching_tool = tool
                    break
        
        if not matching_tool:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
            
        try:
            # Prepare request parameters
            params = {}
            headers = {}
            json_data = {}
            if arguments:
                if matching_tool.method == "GET":
                    params = arguments
                else:
                    json_data = arguments
                    headers = {'Content-Type': 'application/json'}
            # Execute API call
            resp = async_client.request(
                method=matching_tool.method,
                base_url=matching_tool.origin,
                path=matching_tool.path,
                params=params,
                headers=headers,
                json_data=json_data,
                auth_config=matching_tool.auth_config,
                stream=False
            )
            result = ""
            async for data in resp:
                result = data
            
            return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            
        except Exception as e:
            logger.error(f"Error calling tool {name}: {str(e)}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error calling tool: {str(e)}")]
    
    # Add Prompts support
    @server.list_prompts()
    async def handle_list_prompts() -> list[types.Prompt]:
        """List available prompts"""
        prompts = []
        
        # Get prompts from database
        async with get_async_session_ctx() as db_session:
            # Get MCP server
            db_server = await db_session.execute(
                select(MCPServer)
                .options(
                    selectinload(MCPServer.tools).selectinload(MCPTool.tool),
                    selectinload(MCPServer.prompts)
                )
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                return []
            
            # Return default prompts for this MCP server
            prompts.append(types.Prompt(
                name=f"{mcp_name}-help", 
                description=f"Get help about how to use {mcp_name} tools",
                arguments=[]
            ))
            
            # Add stored prompts
            for prompt in server_obj.prompts:
                prompt_args = []
                if prompt.arguments:
                    for arg in prompt.arguments:
                        prompt_args.append(types.PromptArgument(
                            name=arg.get("name"),
                            description=arg.get("description", ""),
                            required=arg.get("required", False)
                        ))
                
                prompts.append(types.Prompt(
                    name=prompt.name,
                    description=prompt.description,
                    arguments=prompt_args
                ))
            
            # Add tool-specific prompts
            for mcp_tool in server_obj.tools:
                tool = mcp_tool.tool
                # Get tool details
                tool_data = await get_tool(str(tool.id), user, db_session)
                
                # Create a prompt for each tool with its parameters as arguments
                prompt_args = []
                
                if tool_data.parameters.get('body'):
                    # For body parameters, create a single argument for the JSON body
                    prompt_args.append(types.PromptArgument(
                        name="body", 
                        description="JSON body for the request",
                        required=True
                    ))
                else:
                    # For other parameter types, create an argument for each required parameter
                    for param_type in ['query', 'path', 'header']:
                        for param in tool_data.parameters.get(param_type, []):
                            if param.get('required'):
                                prompt_args.append(types.PromptArgument(
                                    name=param.get('name'),
                                    description=param.get('description') or f"{param_type} parameter",
                                    required=True
                                ))
                
                prompts.append(types.Prompt(
                    name=f"use-{tool_data.name}",
                    description=f"Create a prompt to use the {tool_data.name} tool",
                    arguments=prompt_args
                ))
        
        return prompts
        
    @server.get_prompt()
    async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        """Get a specific prompt template"""
        async with get_async_session_ctx() as db_session:
            # Get MCP server
            db_server = await db_session.execute(
                select(MCPServer)
                .options(
                    selectinload(MCPServer.tools).selectinload(MCPTool.tool),
                    selectinload(MCPServer.prompts)
                )
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                raise ValueError(f"MCP server not found: {mcp_name}")
            
            # Collect all tool IDs
            tool_ids = [str(mcp_tool.tool_id) for mcp_tool in server_obj.tools]
            
            # Batch retrieve tool objects
            tool_map = await get_tools_by_ids(tool_ids, user, db_session)
            
            # Check for custom prompt
            for prompt in server_obj.prompts:
                if prompt.name == name:
                    return types.GetPromptResult(
                        description=prompt.description,
                        messages=[
                            types.PromptMessage(
                                role="user",
                                content=types.TextContent(
                                    type="text", 
                                    text=prompt.template.format(**(arguments or {}))
                                )
                            )
                        ]
                    )
            
            # Handle the help prompt
            if name == f"{mcp_name}-help":
                tool_descriptions = []
                for mcp_tool in server_obj.tools:
                    tool = tool_map.get(str(mcp_tool.tool_id))
                    if not tool:
                        continue
                    tool_descriptions.append(f"- {tool.name}: {tool.description or 'No description available'}")
                
                tool_descriptions_text = "\n".join(tool_descriptions)
                
                return types.GetPromptResult(
                    description=f"Help information for {mcp_name} tools",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text", 
                                text=f"I need help with the {mcp_name} tools. Please provide information about the available tools and how to use them."
                            )
                        ),
                        types.PromptMessage(
                            role="assistant",
                            content=types.TextContent(
                                type="text", 
                                text=f"I'd be happy to help you with the {mcp_name} tools. Here are the available tools:\n\n{tool_descriptions_text}\n\nTo use these tools, you can call them directly or ask me to help you formulate the right parameters for each tool."
                            )
                        )
                    ]
                )
                
            # Handle tool-specific prompts
            if name.startswith("use-"):
                tool_name = name[4:]  # Remove 'use-' prefix
                
                # Find the matching tool
                matching_tool = None
                for mcp_tool in server_obj.tools:
                    tool = tool_map.get(str(mcp_tool.tool_id))
                    if tool and tool.name == tool_name:
                        matching_tool = tool
                        break
                        
                if not matching_tool:
                    raise ValueError(f"Unknown tool: {tool_name}")
                
                # Format parameters to show in the prompt
                params_text = ""
                if arguments:
                    params_text = "\n".join([f"- {k}: {v}" for k, v in arguments.items()])
                
                return types.GetPromptResult(
                    description=f"Prompt to use the {tool_name} tool",
                    messages=[
                        types.PromptMessage(
                            role="user",
                            content=types.TextContent(
                                type="text", 
                                text=f"I want to use the {tool_name} tool with the following parameters:\n{params_text}\n\nPlease help me format this correctly."
                            )
                        ),
                        types.PromptMessage(
                            role="assistant",
                            content=types.TextContent(
                                type="text", 
                                text=f"I'll help you use the {tool_name} tool. Based on the parameters you've provided, here's how you can call it:\n\n```json\n{json.dumps(arguments or {}, indent=2)}\n```\n\nYou can use this with the tool by asking me to 'Call the {tool_name} tool with these parameters.'"
                            )
                        )
                    ]
                )
            
        raise ValueError(f"Unknown prompt: {name}")
        
    # Add Resources support
    @server.list_resources()
    async def handle_list_resources() -> list[str]:
        """List available resources"""
        resources = []
        
        async with get_async_session_ctx() as db_session:
            # Get MCP server with resources and tools
            db_server = await db_session.execute(
                select(MCPServer)
                .options(
                    selectinload(MCPServer.tools).selectinload(MCPTool.tool),
                    selectinload(MCPServer.resources)
                )
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                return []
            
            # Add documentation resources
            resources.append(f"doc://{mcp_name}/overview")
            
            # Add stored resources
            for resource in server_obj.resources:
                resources.append(resource.uri)
            
            # Add tool-specific resources
            for mcp_tool in server_obj.tools:
                tool = mcp_tool.tool
                # Get tool details
                tool_data = await get_tool(str(tool.id), user, db_session)
                resources.append(f"doc://{mcp_name}/tools/{tool_data.name}")
        
        return resources
        
    @server.read_resource()
    async def handle_read_resource(uri: str) -> tuple[str, str]:
        """Read a specific resource"""
        async with get_async_session_ctx() as db_session:
            # Get MCP server with resources and tools
            db_server = await db_session.execute(
                select(MCPServer)
                .options(
                    selectinload(MCPServer.tools).selectinload(MCPTool.tool),
                    selectinload(MCPServer.resources)
                )
                .where(MCPServer.name == mcp_name)
            )
            server_obj = db_server.scalar_one_or_none()
            
            if not server_obj:
                raise ValueError(f"MCP server not found: {mcp_name}")
            
            # Collect all tool IDs
            tool_ids = [str(mcp_tool.tool_id) for mcp_tool in server_obj.tools]
            
            # Batch retrieve tool objects
            tool_map = await get_tools_by_ids(tool_ids, user, db_session)
            
            # Check for stored resources
            for resource in server_obj.resources:
                if resource.uri == uri:
                    return resource.content, resource.mime_type
            
            # Handle documentation resources
            if uri.startswith(f"doc://{mcp_name}/overview"):
                # Create an overview of all tools
                content = f"# {mcp_name} Tools Overview\n\n"
                content += f"This MCP server provides {len(server_obj.tools)} tools:\n\n"
                
                for mcp_tool in server_obj.tools:
                    tool = tool_map.get(str(mcp_tool.tool_id))
                    if not tool:
                        continue
                    
                    content += f"## {tool.name}\n\n"
                    content += f"{tool.description or 'No description available'}\n\n"
                    content += "### Parameters\n\n"
                    
                    if tool.parameters.get('body'):
                        content += "This tool accepts a JSON body with the following schema:\n\n"
                        content += f"```json\n{json.dumps(tool.parameters['body'], indent=2)}\n```\n\n"
                    else:
                        for param_type in ['query', 'path', 'header']:
                            if tool.parameters.get(param_type):
                                content += f"#### {param_type.capitalize()} Parameters\n\n"
                                for param in tool.parameters[param_type]:
                                    content += f"- **{param.get('name')}**: {param.get('description') or 'No description'}"
                                    if param.get('required'):
                                        content += " (Required)"
                                    content += "\n"
                                content += "\n"
                
                return content, "text/markdown"
                
            if uri.startswith(f"doc://{mcp_name}/tools/"):
                # Extract tool name from URI
                tool_name = uri.split('/')[-1]
                
                # Find the matching tool
                matching_tool = None
                for mcp_tool in server_obj.tools:
                    tool = tool_map.get(str(mcp_tool.tool_id))
                    if tool and tool.name == tool_name:
                        matching_tool = tool
                        break
                        
                if not matching_tool:
                    raise ValueError(f"Unknown tool: {tool_name}")
                    
                # Create detailed documentation for this tool
                content = f"# {tool_name}\n\n"
                content += f"{matching_tool.description or 'No description available'}\n\n"
                content += f"Method: {matching_tool.method}\n"
                content += f"Endpoint: {matching_tool.origin}{matching_tool.path}\n\n"
                content += "## Parameters\n\n"
                
                if matching_tool.parameters.get('body'):
                    content += "This tool accepts a JSON body with the following schema:\n\n"
                    content += f"```json\n{json.dumps(matching_tool.parameters['body'], indent=2)}\n```\n\n"
                else:
                    for param_type in ['query', 'path', 'header']:
                        if matching_tool.parameters.get(param_type):
                            content += f"### {param_type.capitalize()} Parameters\n\n"
                            for param in matching_tool.parameters[param_type]:
                                content += f"- **{param.get('name')}**: {param.get('description') or 'No description'}"
                                if param.get('required'):
                                    content += " (Required)"
                                if param.get('default'):
                                    content += f" (Default: {param.get('default')})"
                                content += "\n"
                            content += "\n"
                    
                content += "## Example Usage\n\n"
                content += "```python\n"
                content += f"result = await client.call_tool(\"{tool_name}\", {{\n"
                
                example_params = {}
                if matching_tool.parameters.get('body'):
                    example_params = {"param1": "value1", "param2": "value2"}
                else:
                    for param_type in ['query', 'path', 'header']:
                        for param in matching_tool.parameters.get(param_type, []):
                            example_params[param.get('name')] = f"example_{param.get('name')}"
                            
                content += f"    # Example parameters\n"
                for k, v in example_params.items():
                    content += f"    \"{k}\": \"{v}\",\n"
                content += "}})\n"
                content += "```\n"
                
                return content, "text/markdown"
            
        raise ValueError(f"Unknown resource: {uri}")
    
    return server

def get_main_app():
    """
    Get the main application containing all MCP server routes
    
    Returns:
        ASGI application function for handling all MCP routes
    """
    async def dynamic_mcp_handler(scope, receive, send):
        """ASGI handler for MCP requests"""
        # Get MCP server name from URL
        path = scope["path"]
        path_parts = path.split('/')
        
        if len(path_parts) < 3:
            response = Response("Invalid MCP URL", status_code=400)
            await response(scope, receive, send)
            return
            
        # Create request object
        from starlette.requests import Request
        request = Request(scope=scope, receive=receive)
        
        # Extract user information (in a real implementation, this would be obtained from the request)
        user = {"tenant_id": "default"}
        
        # Check if MCP server exists
        mcp_name = path_parts[2]
        
        async with get_async_session_ctx() as session:
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.name == mcp_name,
                    MCPServer.is_active == True
                )
            )
            if not result.scalar_one_or_none():
                response = Response(f"MCP server '{mcp_name}' not found", status_code=404)
                await response(scope, receive, send)
                return
        
        # Create dynamic server instance
        server = await _create_server_instance(mcp_name, user)
        
        # Create SSE transmission - use empty path prefix
        sse = SseServerTransport("")
        
        # Directly handle SSE connection
        async with sse.connect_sse(scope, receive, send) as streams:
            await server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name=mcp_name,
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    
    return dynamic_mcp_handler

def _convert_parameters_to_schema(parameters: Dict) -> Dict:
    """
    Convert tool parameters to MCP input schema
    
    Args:
        parameters: Tool parameter definition
        
    Returns:
        MCP-compliant input schema
    """
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Handle body parameters
    if parameters.get('body'):
        return parameters['body']
    
    # Handle other parameter types (query, path, header)
    for param_type in ['query', 'path', 'header']:
        for param in parameters.get(param_type, []):
            name = param.get('name')
            if not name:
                continue
                
            prop = {
                "type": param.get('type', 'string'),
                "description": param.get('description', f"{param_type} parameter")
            }
            
            # Add default value if available
            if 'default' in param:
                prop['default'] = param['default']
                
            schema['properties'][name] = prop
            
            # Add required parameters
            if param.get('required'):
                schema['required'].append(name)
    
    return schema

async def add_prompt_template(
    mcp_name: str,
    prompt_name: str,
    description: str,
    arguments: List[Dict[str, Any]],
    template: str,
    session: Optional[AsyncSession] = None
) -> bool:
    """
    Add a prompt template to an MCP server
    
    Args:
        mcp_name: MCP server name
        prompt_name: Prompt template name
        description: Prompt description
        arguments: List of prompt arguments
        template: Prompt template text
        session: Optional database session
        
    Returns:
        Success status
    """
    close_session = False
    if not session:
        session = await get_async_session()
        close_session = True
    
    try:
        # Get the MCP server
        db_server = await session.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        server_obj = db_server.scalar_one_or_none()
        
        if not server_obj:
            return False
        
        # Check if prompt with the same name already exists
        existing_prompt = await session.execute(
            select(MCPPrompt).where(
                MCPPrompt.mcp_server_id == server_obj.id,
                MCPPrompt.name == prompt_name
            )
        )
        existing = existing_prompt.scalar_one_or_none()
        
        if existing:
            # Update existing prompt
            existing.description = description
            existing.arguments = arguments
            existing.template = template
        else:
            # Create new prompt
            prompt = MCPPrompt(
                mcp_server_id=server_obj.id,
                name=prompt_name,
                description=description,
                arguments=arguments,
                template=template
            )
            session.add(prompt)
        
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding prompt template: {e}", exc_info=True)
        await session.rollback()
        return False
    finally:
        if close_session:
            await session.close()

async def add_resource(
    mcp_name: str,
    resource_uri: str,
    content: str,
    mime_type: str = "text/plain",
    session: Optional[AsyncSession] = None
) -> bool:
    """
    Add a resource to an MCP server
    
    Args:
        mcp_name: MCP server name
        resource_uri: Resource URI
        content: Resource content
        mime_type: MIME type of the resource
        session: Optional database session
        
    Returns:
        Success status
    """
    close_session = False
    if not session:
        session = await get_async_session()
        close_session = True
    
    try:
        # Get the MCP server
        db_server = await session.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        server_obj = db_server.scalar_one_or_none()
        
        if not server_obj:
            return False
        
        # Check if resource with the same URI already exists
        existing_resource = await session.execute(
            select(MCPResource).where(
                MCPResource.mcp_server_id == server_obj.id,
                MCPResource.uri == resource_uri
            )
        )
        existing = existing_resource.scalar_one_or_none()
        
        if existing:
            # Update existing resource
            existing.content = content
            existing.mime_type = mime_type
        else:
            # Create new resource
            resource = MCPResource(
                mcp_server_id=server_obj.id,
                uri=resource_uri,
                content=content,
                mime_type=mime_type
            )
            session.add(resource)
        
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding resource: {e}", exc_info=True)
        await session.rollback()
        return False
    finally:
        if close_session:
            await session.close()

async def get_registered_mcp_servers(session: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
    """
    Get information about all registered MCP servers
    
    Args:
        session: Optional database session
        
    Returns:
        List of MCP server information
    """
    close_session = False
    if not session:
        session = await get_async_session()
        close_session = True
    
    try:
        # Query all MCP servers
        result = await session.execute(
            select(MCPServer).where(MCPServer.is_active == True)
        )
        servers = result.scalars().all()
        
        # Format response
        server_list = []
        for server in servers:
            server_list.append({
                "name": server.name,
                "url": f"{SETTINGS.API_BASE_URL}/mcp/{server.name}",
                "description": server.description
            })
            
        return server_list
    except Exception as e:
        logger.error(f"Error getting registered MCP servers: {e}", exc_info=True)
        return []
    finally:
        if close_session:
            await session.close()

async def delete_mcp_server(mcp_name: str, session: Optional[AsyncSession] = None) -> bool:
    """
    Delete an MCP server
    
    Args:
        mcp_name: MCP server name to delete
        session: Optional database session
        
    Returns:
        Success status
    """
    close_session = False
    if not session:
        session = await get_async_session()
        close_session = True
    
    try:
        # Find the server
        result = await session.execute(
            select(MCPServer).where(MCPServer.name == mcp_name)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return False
            
        # Alternatively, you can set is_active to False instead of deleting
        # server.is_active = False
        # await session.commit()
        
        # Delete server from database
        await session.execute(
            delete(MCPServer).where(MCPServer.name == mcp_name)
        )
        await session.commit()
            
        return True
    except Exception as e:
        logger.error(f"Error deleting MCP server: {e}", exc_info=True)
        await session.rollback()
        return False
    finally:
        if close_session:
            await session.close()

async def get_tool_mcp_mapping(session: Optional[AsyncSession] = None) -> Dict[str, str]:
    """
    Get the mapping from tool ID to MCP server name
    
    Args:
        session: Optional database session
        
    Returns:
        Mapping dictionary
    """
    close_session = False
    if not session:
        session = await get_async_session()
        close_session = True
    
    try:
        # Query MCPTool table to get tool to MCP server mapping
        result = await session.execute(
            select(MCPTool, MCPServer)
            .join(MCPServer, MCPTool.mcp_server_id == MCPServer.id)
            .where(MCPServer.is_active == True)
        )
        mappings = result.all()
        
        # Format response
        mapping_dict = {}
        for mcp_tool, mcp_server in mappings:
            mapping_dict[str(mcp_tool.tool_id)] = mcp_server.name
            
        return mapping_dict
    except Exception as e:
        logger.error(f"Error getting tool MCP mapping: {e}", exc_info=True)
        return {}
    finally:
        if close_session:
            await session.close()

# No longer need to initialize MCP servers on startup
# Instead, servers are created dynamically for each request 

def get_coin_api_mcp_service(user):
    """
    Create an MCP server instance for the built-in coin-api service
    
    Args:
        user: User information for authorization
        
    Returns:
        Server instance configured with handlers
    """
    from agents.agent.mcp import coin_api_mcp  # Local import to avoid circular dependency
    
    logger.info("Creating coin-api MCP service instance")
    return coin_api_mcp.server.server
