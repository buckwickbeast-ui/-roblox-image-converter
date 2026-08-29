from flask import Flask, request, jsonify
import requests
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import os

app = Flask(__name__)

MAX_IMAGE_SIZE = 10 * 1024 * 1024

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "service": "Roblox Image Stroke Converter"
    })


@app.post("/convert")
def convert():
    data = request.get_json(silent=True) or {}
    url = data.get("url")

    if not isinstance(url, str) or not url.strip():
        return jsonify({
            "error": "Missing image URL"
        }), 400

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        return jsonify({
            "error": "URL must start with http:// or https://"
        }), 400

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=(10, 20),
            allow_redirects=True,
            stream=True
        )

        if response.status_code == 429:
            return jsonify({
                "error": "The image host is rate-limiting the converter.",
                "details": (
                    "Try a different direct image URL or an image host "
                    "that permits automated downloads."
                ),
                "source_status": 429
            }), 400

        if response.status_code >= 400:
            return jsonify({
                "error": "Image host returned an error.",
                "details": f"HTTP {response.status_code}",
                "source_status": response.status_code
            }), 400

        content_type = (
            response.headers.get("Content-Type", "")
            .lower()
        )

        content = response.content

        if len(content) > MAX_IMAGE_SIZE:
            return jsonify({
                "error": "Image is larger than 10 MB."
            }), 400

        if not content:
            return jsonify({
                "error": "The image host returned an empty response."
            }), 400

        try:
            image = Image.open(
                BytesIO(content)
            )
            image.load()
        except UnidentifiedImageError:
            return jsonify({
                "error": "The URL did not return a supported image.",
                "details": (
                    "Use a direct PNG, JPEG, or WebP image URL. "
                    f"Content-Type received: {content_type or 'unknown'}"
                )
            }), 400

        image = image.convert("L")

        image.thumbnail((128, 128))

        width, height = image.size
        pixels = image.load()

        strokes = []

        for y in range(height):
            stroke = []

            for x in range(width):
                brightness = pixels[x, y]

                if brightness < 160:
                    stroke.append({
                        "x": round(
                            x / max(width - 1, 1),
                            4
                        ),
                        "y": round(
                            y / max(height - 1, 1),
                            4
                        )
                    })
                else:
                    if len(stroke) >= 2:
                        strokes.append(stroke)

                    stroke = []

            if len(stroke) >= 2:
                strokes.append(stroke)

        return jsonify({
            "width": width,
            "height": height,
            "strokes": strokes
        })

    except requests.Timeout:
        return jsonify({
            "error": "Image download timed out.",
            "details": "The image host took too long to respond."
        }), 400

    except requests.RequestException as e:
        return jsonify({
            "error": "Could not download image.",
            "details": str(e)
        }), 400

    except Exception as e:
        return jsonify({
            "error": "Could not convert image.",
            "details": str(e)
        }), 400


if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
