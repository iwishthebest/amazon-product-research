from amazon_release.images import extract_primary_image_url


def test_extract_primary_image_url_reads_amazon_color_images_json():
    html = r'''<script>"colorImages": { "initial": A.$.parseJSON('[{"hiRes":"https://m.media-amazon.com/images/I/REAL_MAIN._AC_SL1500_.jpg","large":"https://m.media-amazon.com/images/I/LARGE.jpg"}]') }</script>'''
    assert extract_primary_image_url(html) == "https://m.media-amazon.com/images/I/REAL_MAIN._AC_SL1500_.jpg"


def test_extract_primary_image_url_returns_none_when_no_product_image_exists():
    assert extract_primary_image_url("<html><title>Server Busy</title></html>") is None


def test_extract_primary_image_url_falls_back_to_large_image_when_hires_is_missing():
    html = r'''<script>"colorImages":{"Pink":[{"large":"https://m.media-amazon.com/images/I/LARGE_MAIN._AC_.jpg","thumb":"https://m.media-amazon.com/images/I/THUMB.jpg"}]}</script>'''

    assert extract_primary_image_url(html) == "https://m.media-amazon.com/images/I/LARGE_MAIN._AC_.jpg"
