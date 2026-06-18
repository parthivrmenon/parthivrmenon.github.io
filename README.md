# parthivrmenon.github.io

Build the assets for my Website [parthivrmenon.github.io](https://parthivrmenon.github.io/)

## Setup

The first time

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Every other time

```bash
source .venv/bin/activate
```

## How to add a new Post

Add the markdown to `posts/` with appropriate frontmatter

```bash
# posts/my-awesome-post.md
---
title: "Hello World"
date: "2021-01-01"
slug: "hello-world"
---

# Hello World
...

```

Run the build script

```bash
(venv) python build.py
```

The script does two things:
- adds a new post page to `docs/posts` 
- add a link to the page under `posts.html`. The links sorted based on the `date` field in the frontmatter.

## How to Preview

After running the build script

```bash
python -m http.server 8000 --directory docs

# Visit `http://localhost:8000`.

```


## Publish

Github Pages will automatically publish anything that is pushed to the main branch's `/docs` directory so all you need to do is push the latest changes.
