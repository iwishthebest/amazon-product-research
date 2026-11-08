import json

from amazon_release import images
from amazon_release.images import enrich_snapshot_images, extract_primary_image_url


def test_extract_primary_image_url_reads_amazon_color_images_json():
    html = r'''<script>"colorImages": { "initial": A.$.parseJSON('[{"hiRes":"https://m.media-amazon.com/images/I/REAL_MAIN._AC_SL1500_.jpg","large":"https://m.media-amazon.com/images/I/LARGE.jpg"}]') }</script>'''
    assert extract_primary_image_url(html) == "https://m.media-amazon.com/images/I/REAL_MAIN._AC_SL1500_.jpg"


def test_extract_primary_image_url_returns_none_when_no_product_image_exists():
    assert extract_primary_image_url("<html><title>Server Busy</title></html>") is None


def test_extract_primary_image_url_falls_back_to_large_image_when_hires_is_missing():
    html = r'''<script>"colorImages":{"Pink":[{"large":"https://m.media-amazon.com/images/I/LARGE_MAIN._AC_.jpg","thumb":"https://m.media-amazon.com/images/I/THUMB.jpg"}]}</script>'''

    assert extract_primary_image_url(html) == "https://m.media-amazon.com/images/I/LARGE_MAIN._AC_.jpg"


def test_enrich_snapshot_images_downloads_existing_direct_image_url(tmp_path, monkeypatch):
    class Response:
        status_code = 200
        headers = {"Content-Type": "image/jpeg"}
        content = b"jpeg" * 400
        text = ""

    class Session:
        def __init__(self):
            self.headers = {}
            self.calls = []

        def get(self, url, timeout):
            self.calls.append(url)
            return Response()

    session = Session()
    monkeypatch.setattr(images.requests, "Session", lambda: session)
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps([{
        "asin": "B0IMAGE123",
        "image_url": "https://images-fe.ssl-images-amazon.com/images/I/MAIN.jpg",
    }]), encoding="utf-8")

    result = enrich_snapshot_images(snapshot, tmp_path / "images", delay_seconds=0)

    assert result == {"downloaded": 1, "skipped": 0, "failed": 0, "total": 1}
    assert session.calls == ["https://images-fe.ssl-images-amazon.com/images/I/MAIN.jpg"]
    assert (tmp_path / "images" / "B0IMAGE123.jpg").read_bytes() == Response.content
