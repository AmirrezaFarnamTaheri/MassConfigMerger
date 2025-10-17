from pathlib import Path


def build():
    """
    Preprocesses HTML files to include header and footer partials.
    """
    print("Starting HTML build process...")

    root_dir = Path(__file__).parent.parent
    includes_dir = root_dir / "_includes"

    header_content = (includes_dir / "header.html").read_text()
    footer_content = (includes_dir / "footer.html").read_text()

    html_files = [
        "index.html",
        "proxies.html",
        "statistics.html",
        "about.html",
    ]

    for file_name in html_files:
        file_path = root_dir / file_name
        if file_path.exists():
            print(f"Processing {file_name}...")
            content = file_path.read_text()

            content = content.replace('<div id="header-placeholder"></div>', header_content)
            content = content.replace('<div id="footer-placeholder"></div>', footer_content)

            file_path.write_text(content)
            print(f"Finished processing {file_name}.")
        else:
            print(f"Warning: {file_name} not found.")


if __name__ == "__main__":
    build()
