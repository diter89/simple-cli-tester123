import os
import json
import datetime
import sys
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
import chromadb
from tools.shared_console import console
from .fireworks_api_client import generate_response
import chromadb
from chromadb.config import Settings

chromadb.Client(Settings(anonymized_telemetry=False))

SESSION_DIR = ".sessions"
MEMORY_DB_PATH = ".chroma_memory"

class LongTermMemory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LongTermMemory, cls).__new__(cls)
            try:
                client = chromadb.PersistentClient(path=MEMORY_DB_PATH)
                cls._instance.collection = client.get_or_create_collection(name="cross_session_memory")
                console.log("[green]Long Term Memory (ChromaDB) connected.[/green]")
            except Exception as e:
                console.log(f"[red]Failed to connect to ChromaDB: {e}[/red]")
                cls._instance.collection = None
        return cls._instance

    def add_memory(self, text: str, metadata: dict = None):
        if not self.collection: return
        try:
            doc_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
            
            final_metadata = metadata or {}
            
            if 'timestamp' not in final_metadata:
                final_metadata['timestamp'] = datetime.datetime.now().isoformat()

            self.collection.add(
                documents=[text], 
                metadatas=[final_metadata], 
                ids=[doc_id]
            )
        except Exception as e:
            console.log(f"[red]Failed to add ChromaDB memory: {e}[/red]")

    def recall_memory(self, query: str, n_results: int = 3) -> list:
        if not self.collection: return []
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            return results['documents'][0] if results and results['documents'] else []
        except Exception as e:
            console.log(f"[red]Failed to recall from ChromaDB: {e}[/red]")
            return []

def list_linear_sessions() -> list:
    if not os.path.exists(SESSION_DIR):
        os.makedirs(SESSION_DIR)
        return []
    files = sorted(
        [f for f in os.listdir(SESSION_DIR) if f.endswith('.json')],
        key=lambda f: os.path.getmtime(os.path.join(SESSION_DIR, f)),
        reverse=True
    )
    return files

def load_linear_session(filename: str) -> list:
    try:
        with open(os.path.join(SESSION_DIR, filename), 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return []

def save_linear_session(messages: list, filename: str):
    try:
        with open(os.path.join(SESSION_DIR, filename), 'w') as f:
            json.dump(messages, f, indent=2)
    except IOError as e:
        console.log(f"[Warning] Failed to save linear session: {e}")

def recall_and_synthesize(query: str):

    console.log(f"[magenta]🧠 Memory Persona activated. Recalling about: '{query}'[/magenta]")
    ltm = LongTermMemory()
    
    recalled_memories = ltm.recall_memory(query, n_results=4)
    
    if not recalled_memories:
        yield "Sorry, it seems like I don't have any memory about that. Maybe we haven't discussed it before."
        return
        
    separator = "\n---\n"
    formatted_memories = separator.join(recalled_memories)

    synthesis_prompt = f"""
    You are an AI trying to remember something from past conversations.
    Based on the relevant memory fragments below, answer the user's current question in a natural and coherent way.
    
    MEMORY FRAGMENTS FROM YOUR DATABASE:
    ---
    {formatted_memories}
    ---

    USER'S CURRENT QUESTION: "{query}"

    YOUR ANSWER (based on the memories above, as if you remember them naturally):
    """
    
    messages = [{"role": "user", "content": synthesis_prompt}]
    try:
        yield from generate_response(messages, stream=True, temperature=0.1)
    except Exception as e:
        console.log(f"[red]Failed to synthesize memory: {e}[/red]")
        yield "Sorry, I found relevant memories but failed to summarize them."

def prompt_session_choice() -> tuple[list, str, str]:
    linear_sessions = list_linear_sessions()
    
    choices = [
        Choice(value="new_linear", name="✨ Start New Linear Session (Per-Session Memory)"),
        Choice(value="new_chroma", name="🧠 Start New Cross-Time Session (Permanent ChromaDB Memory)"),
        Choice(value="continue_chroma", name="🔄 Continue with Cross-Time Memory (ChromaDB)")
    ]
    if linear_sessions:
        choices.append(Choice(value=None, name="------------------", enabled=False))
        for session_file in linear_sessions:
            choices.append(Choice(value=session_file, name=f"📄 Continue Linear Session: {session_file}"))

    chosen_option = inquirer.select(
        message="Choose memory mode and session:",
        choices=choices,
        default="new_linear",
        border=True,
    ).execute()

    if chosen_option == "new_linear":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_filename = f"session_{timestamp}.json"
        console.print(f"Creating new linear session: {new_filename}")
        return [], new_filename, "linear"
        
    elif chosen_option == "new_chroma":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_filename = f"chroma_session_{timestamp}.json"
        console.print(f"Starting new session with permanent ChromaDB memory.")
        return [], new_filename, "chroma"

    elif chosen_option == "continue_chroma":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_filename = f"chroma_session_{timestamp}.json"
        console.print(f"Continuing with permanent ChromaDB memory.")
        return [], new_filename, "chroma"

    else:
        console.print(f"Continuing linear session: {chosen_option}")
        return load_linear_session(chosen_option), chosen_option, "linear"
