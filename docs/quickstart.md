# Quick Start

## Installation

```bash
pip install mempalace-evolve
```

## First Steps

```python
from mempalace_evolve import MemPalace

# Create a memory palace
palace = MemPalace("my_first_palace")

# Store a memory
palace.remember("The API key is stored in environment variable OPENAI_API_KEY")

# Retrieve it
results = palace.recall("where is the API key?")
print(results[0]["content"])
```

## CLI Quick Start

```bash
# Demo mode
mempalace demo

# Interactive playground
mempalace playground

# Store from command line
mempalace remember "Project uses Python 3.12" --room architecture

# Recall
mempalace recall "Python version"

# Evolution
mempalace evolve

# Export
mempalace export --format json
```
