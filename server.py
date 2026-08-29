from flask import Flask, request, jsonify
import requests
from PIL import Image
from io import BytesIO
import os

app = Flask(__name__)

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

    if not url or not isinstance(url, str):
        return jsonify({
            "error": "Missing image URL"
        }), 400

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        if len(response.content) > 10 * 1024 * 1024:
            return jsonify({
                "error": "Image is larger than 10 MB"
            }), 400

        image = Image.open(
            BytesIO(response.content)
        ).convert("L")

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

    except requests.RequestException as e:
        return jsonify({
            "error": "Could not download image",
            "details": str(e)
        }), 400

    except Exception as e:
        return jsonify({
            "error": "Could not convert image",
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
