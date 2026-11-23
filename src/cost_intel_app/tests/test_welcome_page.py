"""Local welcome-page routing and provenance regression tests."""

from html.parser import HTMLParser

from starlette.testclient import TestClient

from cost_intel_app.server import mcp


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs if key == "href")


def test_welcome_has_local_documentation_links():
    with TestClient(mcp.http_app()) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Cost Intelligence" in response.text
        assert "Demonstration data" in response.text
        assert "Content-Security-Policy" in response.headers
        parser = _Links()
        parser.feed(response.text)
        assert {"/quickstart", "/methodology", "/data-sources"} <= set(parser.hrefs)
        assert all(link.startswith("/") for link in parser.hrefs)
        for link in set(parser.hrefs):
            page = client.get(link)
            assert page.status_code == 200
            assert page.headers["content-type"].startswith("text/html")
            assert "https://" not in page.text
            assert "<script" not in page.text


def test_documentation_explains_launch_and_provenance():
    with TestClient(mcp.http_app()) as client:
        quickstart = client.get("/quickstart").text
        methodology = client.get("/methodology").text
        sources = client.get("/data-sources").text
    assert "ppi_basket" in quickstart and "/mcp" in quickstart
    assert "not a browser page" in quickstart
    assert "normalize" in methodology.lower()
    assert "not live Bureau of Labor Statistics" in sources
    assert "does not assert PARS cost baselines" in sources
