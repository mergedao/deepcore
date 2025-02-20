

ANSWER_PROMPT = """If you are confident in your answer, respond with:

Final Answer: [Your answer here]"""

CLARIFY_PROMPT = """If you need to clarify the user's intent or gather more information before providing a confident answer, respond with:

Tool Clarify: [Your clarification or question here]"""

TOOLS_PROMPT = """### Decision Flow for Responses  

1. **Determine Requirement**:  
   - Assess whether tool usage is necessary based on the user's query and the information provided.  

2. **Generate Output**:  
   - **If Tool Usage is Required**: Generate JSON output first, adhering to the tool's schema, without including a Final Answer at this stage.  
   - **If Tool Usage is NOT Required**: Directly provide a Final Answer in plain text.  

3. **If Clarification is Needed**:  
   - Provide a response labeled as `Tool Clarify` to request additional details from the user.  
   - This can be included alongside a `Final Answer` in plain text if applicable.  

---

### Output Examples  

#### **When Using a Tool**:  
If the tool's output can directly satisfy the user's question:  
```json
{
    "type": "api",
    "function": {
        "name": "example_tool",
        "parameters": {
            "header": {},
            "query": {},
            "path": {},
            "body": {}
        }
    }
}
```
- **header**: Extract relevant header information if present in the input.
- **query**: Identify and extract query parameters from the input.
- **path**: Capture the API path variables based on the user's intent.
- **body**: Extract the request body, ensuring it matches the expected API payload.

or

```json
{
    "type": "function",
    "function": {
        "name": "example_tool",
        "parameters": {
            "param1": "value1",
            "param2": "value2"
        }
    }
}
```
### Error Handling  

1. **When Input is Insufficient for Tool Invocation**:  
   - Generate a response to request clarification:  
      Tool Clarify: <Specific details about what clarification is needed>.

2. **When Tool Usage Fails**:  
   - Provide an error response indicating the failure and possible reasons.  

"""