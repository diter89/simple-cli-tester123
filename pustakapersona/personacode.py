from tools.shared_console import console
from core.fireworks_api_client import generate_response
from tools.lang_utils import detect_target_language_from_messages
from typing import List, Dict, Generator, Optional
from InquirerPy import inquirer
from InquirerPy.validator import EmptyInputValidator
from rich.panel import Panel
import os
import subprocess
import tempfile

def run_code_persona(user_request: str, messages: List[Dict]) -> Generator[str, None, None]:

    console.log(f"[yellow]💻 Persona 'code' streaming v2.4 starting... Request: '{user_request}'[/yellow]")
    
    try:
        language = _detect_language(user_request)
        target_language = detect_target_language_from_messages(messages)
        console.log(f"[green]...Language detected: {language}[/green]")
        
        recent_context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-4:]])
        
        code_gen_prompt = f"""
You are an expert programmer. Your task is to write a clean, efficient, and well-commented code snippet based on the user's request, considering the recent conversation context.

RECENT CONVERSATION:
---
{recent_context}
---

CURRENT USER REQUEST: "{user_request}"
Programming Language: {language}
LANGUAGE: {target_language} (write any explanations and notes in this language)

INSTRUCTIONS:
1. First provide a brief explanation of what you're creating (1-2 sentences)
2. Then provide the code with proper markdown formatting
3. Include helpful comments in the code
4. End with any important usage notes if needed

Format your response in markdown for better display.
"""
        
        messages_for_llm = [{"role": "user", "content": code_gen_prompt}]
        
        console.log(f"[yellow]...Code generation in progress for {language}...[/yellow]")
        
        for chunk in generate_response(messages_for_llm, stream=True, temperature=0.1):
            if chunk:
                yield chunk
        
        console.log(f"[green]✅ Code streaming completed for {language}[/green]")

    except Exception as e:
        console.log(f"[red]❌ Critical error in code persona streaming: {e}[/red]")
        yield f"**Error**: Sorry, a critical error occurred while generating code: {str(e)}"

def run_code_persona_non_streaming(user_request: str, messages: List[Dict]):

    console.log(f"[yellow]💻 Persona 'code' non-streaming v2.4 starting... Request: '{user_request}'[/yellow]")
    
    try:
        language = _detect_language(user_request)
        target_language = detect_target_language_from_messages(messages)
        console.log(f"[green]...Language detected: {language}[/green]")
        
        recent_context = "\n".join([f"{m['role']}: {m['content']}" for m in messages[-4:]])
        
        code_gen_prompt = f"""
You are an expert programmer. Your task is to write a clean, efficient, and well-commented code snippet based on the user's request, considering the recent conversation context.

RECENT CONVERSATION:
---
{recent_context}
---

CURRENT USER REQUEST: "{user_request}"
Programming Language: {language}
LANGUAGE: {target_language} (write any explanations and notes in this language, but output MUST be only raw code)

CRITICAL INSTRUCTIONS:
1. Output ONLY the raw source code.
2. ABSOLUTELY DO NOT include any explanations, introductory text, or Markdown backticks (```).
3. The output must be pure, raw code, ready to be saved directly to a file.
"""
        
        messages_for_llm = [{"role": "user", "content": code_gen_prompt}]
        
        console.log(f"[yellow]...Code generation in progress for {language}...[/yellow]")
        
        code_chunks = []
        for chunk in generate_response(messages_for_llm, stream=True, temperature=0.1):
            if chunk:
                code_chunks.append(chunk)
        
        raw_code = "".join(code_chunks).strip()
        
        if raw_code.startswith(f"```{language}"): raw_code = raw_code.split("\n", 1)[1]
        if raw_code.startswith("```"): raw_code = raw_code[3:]
        if raw_code.endswith("```"): raw_code = raw_code[:-3]
        raw_code = raw_code.strip()

        console.log(f"[green]✅ Code generation successful. Length: {len(raw_code)} chars.[/green]")
        
        return {"language": language, "code": raw_code}

    except Exception as e:
        console.log(f"[red]❌ Critical error in code persona: {e}[/red]")
        return {"language": "text", "code": f"Sorry, an error occurred while creating code: {e}"}

def post_code_interaction(code: str, language: str, context: List[Dict]):
    if not code:
        return 

    try:
        choice = inquirer.select(
            message="Choose next action:",
            choices=[
                {"name": "Save Code", "value": "save"},
                {"name": "Edit Code", "value": "edit"},
                {"name": "Continue Chat", "value": "continue"},
            ],
            default="continue",
            qmark=":",
            amark=":",
            border=True,
        ).execute()

        if choice == "save":
            _save_code(code, language, context)
        elif choice == "edit":
            _edit_code(code, language)

    except Exception as e:
        console.log(f"[yellow]⚠️  Cannot display interactive menu: {e}[/yellow]")

def _save_code(code: str, language: str, context: List[Dict]):
    suggested_name = _generate_filename(code, context)
    
    filename = inquirer.text(
        message="Enter filename (without extension):",
        default=suggested_name,
        validate=EmptyInputValidator("Filename cannot be empty"),
        qmark=":",
        amark="❯",
    ).execute()
    
    extension = _get_extension(language)
    full_filename = f"{filename}.{extension}"

    with open(full_filename, 'w', encoding='utf-8') as f:
        f.write(code)
    
    console.log(Panel(f"{os.path.abspath(full_filename)}",title="Code saved successfully",highlight=True))

def _edit_code(code: str, language: str):
    extension = _get_extension(language)
    
    with tempfile.NamedTemporaryFile(mode='w+', suffix=f".{extension}", delete=False, encoding='utf-8') as tf:
        tf.write(code)
        temp_path = tf.name

    editor = os.getenv('EDITOR', 'nano')
    console.print(f"\n[yellow]Opening editor '{editor}'... Close editor to continue.[/yellow]")
    
    try:
        subprocess.run([editor, temp_path], check=True)
        console.print("[green]✅ Editing completed.[/green]\n")
    except FileNotFoundError:
        console.print(f"[red]Error: Editor '{editor}' not found. Set $EDITOR environment variable.[/red]")
    except Exception as e:
        console.print(f"[red]Error opening editor: {e}[/red]")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def _generate_filename(code: str, context: List[Dict]) -> str:
    console.log("[grey50]🧠 Generating suggested filename...[/grey50]")
    context_str = "\n".join([f"{m['role']}: {m['content']}" for m in context[-5:]])
    prompt = f"""
    Based on the following conversation context and the generated code, suggest a concise, single, snake_case filename without the extension.
    Example: create_rich_table, api_data_fetcher, user_login_script

    Conversation:
    ---
    {context_str}
    ---
    Generated Code Snippet:
    ---
    {code[:300]}...
    ---
    Suggested Filename (one word, snake_case):
    """
    try:
        messages = [{"role": "user", "content": prompt}]
        response_gen = generate_response(messages, stream=False, temperature=0.2)
        filename = "".join(response_gen).strip().replace(" ", "_").replace("-", "_")
        return ''.join(filter(lambda char: char.isalnum() or char == '_', filename)) or "new_code"
    except Exception:
        return "new_code"

def _get_extension(language: str) -> str:
    ext_map = {
        "python": "py", "javascript": "js", "html": "html", "css": "css", 
        "php": "php", "bash": "sh", "typescript": "ts", "java": "java", "csharp": "cs"
    }
    return ext_map.get(language, "txt")

def _detect_language(user_request: str) -> str:
    prompt = f'Analyze the user\'s request and identify the programming language. Respond with only a single, lowercase word (e.g., "python"). Default to "python".\nUser Request: "{user_request}"\nLanguage:'
    messages = [{"role": "user", "content": prompt}]
    try:
        lang_generator = generate_response(messages, stream=False, temperature=0.0)
        language = "".join(lang_generator).strip().lower()
        return ''.join(filter(str.isalnum, language)) or "python"
    except Exception:
        return "python"
