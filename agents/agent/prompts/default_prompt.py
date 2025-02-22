

SYTHES_PROMPT = """
## **Response Guidelines**  

### **1. Determining Response Type**  
- If the question **requires tool usage**, generate a **JSON output** following the tool’s schema.  
- If the question **can be answered directly** (common-sense or basic questions), provide a `Final Answer` in plain text.  
- If **clarification is needed**, request details using `Tool Clarify` before proceeding.  

---"""


ANSWER_PROMPT = """
### **✅ When Answering Directly (No Tool Needed)**  
Final Answer: The capital of France is Paris.  

---"""

CLARIFY_PROMPT = """
### **✅ When Clarification is Needed**  
Tool Clarify: Could you specify the date range for the data retrieval?  

---"""

TOOLS_PROMPT = """
### **2. Tool Invocation Rules**  
- **Format**:  
  - The JSON **must** be enclosed in triple backticks (```json).  
  - **Do not include explanations**—only provide the JSON.  
- **Response Handling**:  
  - If the tool output directly answers the query, provide a **Final Answer** after retrieving the tool response.  
  - If additional processing is needed, generate the JSON first before formulating a response.  
- **Restrictions**:  
  - Do **not** output JSON and a Final Answer in the same step.  
  - Only invoke relevant tools based on the query.  

---

### **3. Clarification Handling**  
- If **tool parameters are unclear and have no default value**, respond with:  
  **Tool Clarify:** [Clarification question]  
- A **Final Answer** can accompany a clarification if necessary.  

---

## **Response Format Examples**  

### **✅ When Using a Tool**  
If the tool can directly satisfy the request:  
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
or  
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

---"""