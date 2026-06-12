from pathlib import Path
import markdown
from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass, asdict

env = Environment(loader=FileSystemLoader("."))
INDEX_TEMPLATE = env.get_template("templates/index.html")
POST_TEMPLATE = env.get_template("templates/post.html")


@dataclass
class Post:
    title: str
    date: str
    slug: str
    content: str


@dataclass
class Index:
    title: str
    posts: list[str]


def parse_post_markdown(content: str) -> Post:
    """Parse markdown into frontmatter and HTML"""
    _, meta, body = content.split("---", maxsplit=2)
    frontmatter = {}
    for line in meta.strip().splitlines():
        k, v = line.split(":", 1)
        frontmatter[k.strip()] = v.strip().strip('"')
    html = markdown.markdown(body, extensions=["fenced_code", "tables"])
    return Post(
        title=frontmatter["title"],
        date=frontmatter["date"],
        slug=frontmatter["slug"],
        content=html,
    )


def create_post_link(post: Post):
    return f'<a href="posts/{post.slug}.html">{post.title}</a> <span class="meta">{post.date}</span>'


def main():
    post_links = []
    for post_md_file in Path("posts").glob("*.md"):
        content = post_md_file.read_text()
        post = parse_post_markdown(content)

        post_links.append(create_post_link(post))

        post_html = POST_TEMPLATE.render(**asdict(post))
        out = Path(f"docs/posts/{post.slug}.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(post_html)

    # Render Index
    index = Index(title="Parthiv's Blog", posts=post_links)
    index_html = INDEX_TEMPLATE.render(**asdict(index))
    index_file = Path("docs/index.html")
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(index_html)


if __name__ == "__main__":
    main()
