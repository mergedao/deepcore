

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

- **Decision Making**:  
  - Determine whether to **invoke a tool, combine multiple tool results step by step, or respond directly** based on the query.  
  - If multiple tools are needed, **invoke them sequentially**, making a decision after each tool's response.  
  - **If a single tool can fulfill the request, invoke it directly before considering additional tools.**  

- **Format**:  
  - The JSON **must** be enclosed in triple backticks (```json).  
  - **Do not include explanations**—only provide the JSON.  

- **Response Handling**:  
  - If a tool’s output fully answers the query, return a **Final Answer** after retrieving the response.  
  - If additional processing is required, invoke the necessary tool first, then construct the next step.  

- **Restrictions**:  
  - Do **not** output JSON and a Final Answer in the same step.  
  - Only invoke **one tool at a time**—each tool's output should be analyzed before deciding on the next step.  

- **For API Tools**:  
  - When the tool type is **api**, extracted parameters **must** be structured into four levels: `header`, `query`, `path`, and `body`.  
  - Do **not** flatten these parameters into a single level.  

---

### **3. Clarification Handling**  
- **Only ask for clarification if an essential parameter is missing and cannot be reasonably inferred from the user’s query.**  
- **If the required parameter can be inferred, use the inferred value instead of asking for clarification.**  
- If clarification is needed, format the response as follows:  Tool Clarify: [Clarification question]
- **Avoid unnecessary clarifications**—prioritize efficiency in tool invocation.  

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
## **Response Format Examples**

### **✅ Correct Example**
For instance, if the user says:  
*Generate a formal notification about the latest product update*,  
the correct API call should be:
```json
{
  "type": "api",
  "function": {
    "name": "notifyUser",
    "parameters": {
      "header": {},
      "query": {
        "message": "Generate a formal notification about the latest product update."
      },
      "path": {},
      "body": {}
    }
  }
}
```

### **❌ Incorrect Example**
An incorrect API call would flatten the parameters instead of using the required four levels:
```json
{
  "type": "api",
  "function": {
    "name": "notifyUser",
    "parameters": {
      "message": "Generate a formal notification about the latest product update."
    }
  }
}
```
This is incorrect because it does not include the required four levels: `header`, `query`, `path`, and `body`.
## **Response Format Examples**

### **✅ Correct Example**
For instance, if the user says:  
*Generate a formal notification about the latest product update*,  
the correct API call should be:
```json
{
  "type": "api",
  "function": {
    "name": "notifyUser",
    "parameters": {
      "header": {},
      "query": {
        "message": "Generate a formal notification about the latest product update."
      },
      "path": {},
      "body": {}
    }
  }
}
```

### **❌ Incorrect Example**
An incorrect API call would flatten the parameters instead of using the required four levels:
```json
{
  "type": "api",
  "function": {
    "name": "notifyUser",
    "parameters": {
      "message": "Generate a formal notification about the latest product update."
    }
  }
}
```
This is incorrect because it does not include the required four levels: `header`, `query`, `path`, and `body`.


---"""