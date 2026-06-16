---
title: "You Don't Need a Framework to Build a Chatbot"
date: "2026-06-14"
slug: "trivi-al"
---

# Building Trivi-Al: a tiny QnA Bot

In this tutorial, we build *Trivi-Al*, a tiny chatbot that can ingest a document and answer questions about it.

We will keep things intentionally simple - No frameworks, no fancy abstractions. Just enough Python to understand how RAG, tool calling, and agentic loops fit together.

## What you will need

* Python 3.x
* An OpenAI API Key


## Setting up

### Creating a virtual environment

From the project folder, run:

```bash
python -m venv venv
```

Then activate it:

```bash
source venv/bin/activate
```

You should now see something like `(venv)` at the start of your terminal prompt. That means any packages we install will go into this project environment.

### Installing dependencies

Create a `requirements.txt` file and add the packages we will use:

```text
openai
python-dotenv
pytest
```

Here is what each package is for:

- `openai` lets us call the LLM
- `python-dotenv` lets us load secrets from a `.env` file
- `pytest` lets us write a few tests as the project grows


Now install the dependencies:

```bash
python -m pip install -r requirements.txt
```


### Setting the API key

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_key_here
```

The `load_dotenv()` call in `main.py` will load this automatically.


## Prompts

We start by creating our prompts as plain markdown files. This keeps them easy to read and edit without touching Python code.

Create a file called `prompts/system_prompt.md`:

```text
Answer the user's question using only information retrieved from the indexed document.

Return only valid JSON.
Do not wrap it in markdown.
Do not include any explanation outside the JSON.

Your response must contain role, content, and tool_call.
Use role='assistant'.
Use content for the natural-language answer to the user.

Before answering any document-related question, you must request exactly one DocStore tool call.

Instructions for searching the document:
1. Extract exactly 1 keyword from the user's query that can be used for search.
2. Use search_document to retrieve k related chunks.
3. Answer based on these retrieved chunks.


Use sample_document only when the user asks for a summary, overview, or does not provide a specific searchable topic.

Request the tool call by setting tool_call.tool_name to the tool name and tool_call.args to a JSON object containing the tool arguments.

Do not answer document-related questions from memory or prior knowledge.
Before receiving a tool result, leave content empty when requesting a tool call.

When the conversation contains a message beginning with 'Tool result from', use that tool result to answer the user's original question.
After receiving a tool result, answer only from the tool result.

If the tool result does not contain enough information, say that the indexed document does not contain enough information.

Do not request another tool call after receiving a tool result.
After receiving a tool result, set tool_call.tool_name to an empty string and tool_call.args to an empty object.

The JSON must match this schema:

{{ response_format }}

Tools:

{{ tools_registry }}
```

## Prompt Management

Next, create `src/prompt_manager.py` which allows us to render our prompts dynamically at runtime.

```python
from pathlib import Path


class PromptManager:
    def __init__(self, template: str):
        self.template = template

    @classmethod
    def from_file(cls, path: str | Path):
        return cls(Path(path).read_text())

    def render(self, **variables: str) -> str:
        rendered = self.template

        for key, value in variables.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", value)

        return rendered
```

## Testing the PromptManager

Let us write a test to ensure that prompts can be rendered correctly.

### Writing the tests

Create `tests/test_prompt_manager.py`:

```python
import pytest
from src.prompt_manager import PromptManager


@pytest.fixture
def sample_template():
    return """Replace {{ this }} with {{ that }}"""


def test_render(sample_template):
    pm = PromptManager(template=sample_template)
    rendered = pm.render(this="that", that="this")
    assert rendered == """Replace that with this"""
```

### Running the tests

```bash
python -m pytest -v
```


## Retrieval - building a simple DocStore

Let us start with the most basic version of retrieval - a simple Document store that allows us to index a document and search within it.

Create a file called `src/doc_store.py`:

```python
import random


class DocStore:
    def __init__(self):
        self.chunks = []

    def index(self, filepath: str) -> int:
        with open(filepath, "r") as f:
            content = f.read()

        self.chunks = content.lower().split("\n\n")
        return len(self.chunks)

    def search(self, query: str, k: int = 5) -> list[str]:
        matches = []
        terms = query.lower().split()

        for chunk in self.chunks:
            if any(term in chunk for term in terms):
                matches.append(chunk)

        return matches[:k]

    def sample(self, k: int = 1) -> list[str]:
        return random.sample(self.chunks, min(k, len(self.chunks)))
```


## Testing the DocStore

Before we wire this into a chatbot, it is worth verifying that the three methods work correctly. We will test against a real file so our assertions are grounded in known content.

### Creating a test fixture

Create a file `data/simple.txt` with a few paragraphs separated by blank lines:

```text
The African elephant is the largest land animal on Earth.
Adult males can weigh up to 6,350 kilograms and stand 3 to 4 meters tall at the shoulder.
Elephants have large ears that help them regulate body temperature in hot climates.
Their trunks contain over 40,000 muscles and can lift objects weighing up to 350 kilograms.

Elephants are herbivores that consume between 150 to 300 kilograms of food per day.
They spend up to 16 hours daily eating grasses, leaves, bark, and fruit.
Due to their massive size, elephants require vast amounts of water and can drink up to 190 liters in a single day.

African Elephants live in matriarchal family groups led by the oldest female.
These herds typically consist of related females and their offspring.
Male elephants leave the herd when they reach puberty and either live alone or form loose bachelor groups.

Elephants communicate using low-frequency sounds called infrasound that travel several kilometers.
They also use body language, touch, and scent signals to communicate with each other.
Their exceptional memory helps them remember water sources and recognize other elephants after years of separation.
```

This gives us 4 chunks, with "elephant" in every chunk and "matriarchal" in exactly one — useful for precise assertions.

### Writing the tests

Create `tests/test_doc_store.py`:

```python
import pytest
from src.doc_store import DocStore


@pytest.fixture
def db():
    db = DocStore()
    db.index("./data/simple.txt")
    return db


def test_index():
    db = DocStore()
    # simple.txt has 4 paragraphs separated by \n\n
    assert db.index("./data/simple.txt") == 4
    assert len(db.chunks) == 4


def test_search(db):
    # "matriarchal" appears in exactly 1 chunk
    search_results = db.search(query="matriarchal", k=3)
    assert len(search_results) == 1

    # search is case-insensitive
    search_results = db.search(query="Matriarchal", k=3)
    assert len(search_results) == 1

    # "elephant" appears in all 4 chunks, k=1 should limit to 1
    search_results = db.search(query="elephant", k=1)
    assert len(search_results) == 1

    search_results = db.search(query="nonexistent", k=3)
    assert len(search_results) == 0

    # multi-term query matches chunks containing any term
    search_results = db.search(query="elephant matriarchal", k=10)
    assert len(search_results) == 4


def test_sample(db):
    # normal case: k within bounds
    assert len(db.sample(k=3)) == 3

    # k exceeds chunk count — should return all chunks
    assert len(db.sample(k=100)) == 4

    # k=0 — should return empty list
    assert len(db.sample(k=0)) == 0
```

### Running the tests

```bash
python -m pytest -v
```

You should see all three tests pass.

## Tools

Create `src/tools.py` to define the available tools and their signatures:

```python
from src.doc_store import DocStore


TOOLS_REGISTRY = {
    "sample_document": {"k": 1},
    "search_document": {"query": "", "k": 5},
}


def sample_document(store: DocStore, k: int) -> list[str]:
    """Return k random chunks from DocStore"""
    return store.sample(k)


def search_document(store: DocStore, query: str, k: int) -> list[str]:
    """Return top-k chunks that are similar to query"""
    return store.search(query, k)
```

`TOOLS_REGISTRY` describes the tools and their expected arguments. This gets injected into the system prompt so the LLM knows what it can ask for.


## LLM Client

Create `src/llm_client.py` to handle all communication with the LLM:

```python
import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI


@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str
    tool_call: dict[str, Any] | None = None


class LLMClient:
    def __init__(self, client: OpenAI, system_prompt: str):
        self.client = client
        self.system_prompt = system_prompt

    def invoke(self, conversation: list[Message]) -> Message:
        messages = [{"role": "system", "content": self.system_prompt}]

        for message in conversation:
            messages.append({"role": message.role, "content": message.content})

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
        )
        result = response.choices[0].message.content
        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError as err:
            raise ValueError(f"Expected valid JSON from LLM, got: {result}") from err
        return Message(
            role=parsed_result["role"],
            content=parsed_result["content"],
            tool_call=parsed_result["tool_call"],
        )
```

`Message` is a dataclass for conversation turns. `LLMClient.invoke` formats the conversation, calls the API, and parses the JSON response back into a `Message`.

## Agentic Loop

Now we put it all together in `main.py`.

### Prompt Config

Define the response shape the model must always return, and the paths to our prompt files:

```python
# main.py

import json
from pathlib import Path

RESPONSE_FORMAT = {
    "role": "assistant",
    "content": "",
    "tool_call": {"tool_name": "", "args": {}},
}

PROMPT_FILE = Path(__file__).parent / "prompts" / "system_prompt.md"
```

### handle_turn

`handle_turn` manages one full round-trip: it appends the user message, calls the LLM, runs any requested tool, then calls the LLM again with the result. The `conversation` list is passed by reference so every turn accumulates in the caller's list — giving the LLM full history on each call.

```python
from src.doc_store import DocStore
from src.llm_client import LLMClient, Message
from src.tools import sample_document, search_document


def handle_turn(
    query: str,
    conversation: list[Message],
    llm_client: LLMClient,
    doc_store: DocStore,
) -> Message:
    conversation.append(Message(role="user", content=query))
    ai_msg = llm_client.invoke(conversation)
    conversation.append(ai_msg)

    if ai_msg.tool_call and ai_msg.tool_call.get("tool_name"):
        tool_name = ai_msg.tool_call["tool_name"]
        tool_args = ai_msg.tool_call.get("args", {})

        if tool_name == "sample_document":
            tool_result = sample_document(doc_store, **tool_args)
        elif tool_name == "search_document":
            tool_result = search_document(doc_store, **tool_args)
        else:
            tool_result = f"Unknown tool: {tool_name}"

        tool_msg = Message(role="user", content=f"Tool result from {tool_name}: {tool_result}")
        conversation.append(tool_msg)

        final_msg = llm_client.invoke(conversation)
        conversation.append(final_msg)
        return final_msg

    return ai_msg
```

### main — Ask Mode

Index the document, build the client, and run the loop:

```python
from dotenv import load_dotenv
from openai import OpenAI
from src.prompt_manager import PromptManager
from src.tools import TOOLS_REGISTRY

_ = load_dotenv()
client = OpenAI()

docs = DocStore()
_ = docs.index("data/simple.txt")

system_prompt = PromptManager.from_file(PROMPT_FILE).render(
    response_format=json.dumps(RESPONSE_FORMAT),
    tools_registry=json.dumps(TOOLS_REGISTRY),
)
llm = LLMClient(client, system_prompt)

conversation = []

while True:
    user_input = input("User: ")

    if user_input.lower() == "exit":
        break

    response = handle_turn(user_input, conversation, llm, docs)
    print(response.content)
```

At this point we have a working document chatbot.

## Running the App

```bash
python main.py
```

Type `exit` to quit.

## Tests

Run the full test suite:

```bash
python -m pytest -v
```

