### Get free proxylis: https://www.webshare.io/ (Optional)
### Get free apikey: https://app.fireworks.ai/

### Example: 
```bash
export FIREWORKS_API_KEY="<your-apikey>"
```
### run script:
```python
python3 app.py
```

### How to Add a New Persona ?
1. **Create a File in `pustakapersona/`**: Copy `personareadle.py` as a template. The main function must use `yield` for streaming.
2. **Edit Router in `core/advanced_router.py`**:
   * Add new `INTENT` to the LLM prompt.
   * Add to `VALID_INTENTS`.
   * Add `INTENT` to `tool_name` mapping in `tool_map`.
3. **Edit in `app.py`**:
   * `import` the new function from the persona file.
   * Add the new `tool_name` to the `generator_map_stream` dictionary and link it to the imported function.

### :::
<img width="1356" height="686" alt="Screenshot from 2025-09-22 07-05-24" src="https://github.com/user-attachments/assets/0f3772df-5d54-4aa2-9ecf-1f6ae97712f5" />
