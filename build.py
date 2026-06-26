from pathlib import Path
import shutil
import markdown
from jinja2 import Environment, FileSystemLoader
from dataclasses import dataclass, asdict
from pygments.formatters import HtmlFormatter

env = Environment(loader=FileSystemLoader("."))
INDEX_TEMPLATE = env.get_template("templates/index.html")
POSTS_TEMPLATE = env.get_template("templates/posts.html")
POST_TEMPLATE = env.get_template("templates/post.html")


@dataclass
class Post:
    title: str
    date: str
    slug: str
    content: str


def parse_post_markdown(content: str) -> Post:
    """Parse markdown into frontmatter and HTML"""
    _, meta, body = content.split("---", maxsplit=2)
    frontmatter = {}
    for line in meta.strip().splitlines():
        k, v = line.split(":", 1)
        frontmatter[k.strip()] = v.strip().strip('"')
    html = markdown.markdown(body, extensions=["fenced_code", "tables", "codehilite"])
    return Post(
        title=frontmatter["title"],
        date=frontmatter["date"],
        slug=frontmatter["slug"],
        content=html,
    )


def main():
    shutil.copytree("static", "docs", dirs_exist_ok=True)
    pygments_css = HtmlFormatter(style="monokai").get_style_defs(".codehilite")
    Path("docs/posts/pygments.css").write_text(pygments_css)
    posts = []
    for post_md_file in Path("posts").glob("*.md"):
        content = post_md_file.read_text()
        post = parse_post_markdown(content)
        posts.append(post)

        post_html = POST_TEMPLATE.render(**asdict(post))
        out = Path(f"docs/posts/{post.slug}.html")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(post_html)

    posts.sort(key=lambda p: p.date, reverse=True)

    Path("docs/index.html").write_text(INDEX_TEMPLATE.render())
    Path("docs/posts.html").write_text(POSTS_TEMPLATE.render(posts=posts))


if __name__ == "__main__":
    main()
