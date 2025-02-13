import re


def extract_code_blocks_with_language(markdown_text: str):
    # Regex pattern to match code blocks and optional language specifiers
    pattern = r"```(\w+)?\n(.*?)```"

    # Find all matches (language and content)
    matches = re.findall(pattern, markdown_text, re.DOTALL)

    # Parse results
    code_blocks = []
    for language, content in matches:
        language = (
            language.strip() if language else "plaintext"
        )  # Default to 'plaintext'
        code_blocks.append(
            {"language": language, "content": content.strip()}
        )

    return code_blocks


def extract_md_code(
        markdown_text: str, language: str = None
):
    # Get all code blocks with detected languages
    code_blocks = extract_code_blocks_with_language(markdown_text)

    # Filter by language if specified
    if language:
        code_blocks = [
            block["content"]
            for block in code_blocks
            if block["language"] == language
        ]
    else:
        code_blocks = [
            block["content"] for block in code_blocks
        ]  # Include all blocks

    # Return concatenated content
    return "\n\n".join(code_blocks) if code_blocks else ""
