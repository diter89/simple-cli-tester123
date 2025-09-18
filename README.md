### example: 
```
export FIREWORKS_API_KEY="<apikey>"
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
