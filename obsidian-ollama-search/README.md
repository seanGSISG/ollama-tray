# Obsidian Ollama Semantic Search Plugin

This plugin enables semantic search in your Obsidian vault using Ollama's embedding models.

## How Embedding Models Work

Embedding models like `snowflake-arctic-embed2` are specialized models that convert text into numerical vectors (embeddings). Unlike chat models, they don't generate text - they only produce vector representations.

### Using Embedding Models with Ollama

1. **Pull the model**: `ollama pull snowflake-arctic-embed2:latest`
2. **Embedding models cannot be "run"** - they're used via the API endpoint
3. **Access via API**: The plugin uses the `/api/embeddings` endpoint

### API Usage Example

```bash
curl http://localhost:11434/api/embeddings -d '{
  "model": "snowflake-arctic-embed2:latest",
  "prompt": "Your text to embed"
}'
```

## Installation

1. Clone this repository into your vault's `.obsidian/plugins/` folder
2. Run `npm install` in the plugin directory
3. Run `npm run build`
4. Enable the plugin in Obsidian settings

## Usage

1. Make sure Ollama is running: `ollama serve`
2. Use Command Palette: "Index vault for semantic search"
3. Once indexed, use: "Semantic search" to search

## Settings

- **Ollama URL**: Default `http://localhost:11434`
- **Embedding Model**: Default `snowflake-arctic-embed2:latest`
- **Chunk Size**: Number of words per document chunk
- **Chunk Overlap**: Overlap between chunks for context

## How It Works

1. **Indexing**: Splits documents into chunks and generates embeddings
2. **Search**: Converts query to embedding and finds similar chunks using cosine similarity
3. **Results**: Shows most similar document chunks with similarity scores