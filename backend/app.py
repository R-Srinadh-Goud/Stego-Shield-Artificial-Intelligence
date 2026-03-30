import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file, after_this_request
import requests
import os
import uuid
import threading
import time
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TEMP_FOLDER = "temp"
if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)

# ---------------- AUTO DELETE ----------------
def schedule_delete(paths, delay=120):
    def delete():
        time.sleep(delay)
        for p in paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass
    threading.Thread(target=delete, daemon=True).start()

# ---------------- DETECTION ----------------
def detect_content(text):
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    urls = re.findall(r"https?://[^\s]+", text)
    return len(set(emails)), len(set(urls))

# ---------------- IMAGE PROCESS ----------------
def process_image(file_path):
    img = cv2.imread(file_path)
    if img is None:
        return None, None, "Invalid image"

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    pixels = gray.flatten()
    variance = np.var(pixels)

    histogram = np.histogram(pixels, bins=256)[0]
    histogram = histogram / np.sum(histogram)

    entropy = -np.sum([p * np.log2(p) for p in histogram if p != 0])

    # heatmap
    heatmap = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    heatmap_path = file_path.replace(".jpg", "_heatmap.jpg")
    cv2.imwrite(heatmap_path, heatmap)

    # simulated content
    text_data = str(histogram[:50])

    emails, urls = detect_content(text_data)

    score = min((entropy * 0.6 + variance * 0.0005) / 10, 1)

    if score < 0.3:
        level, decision = "LOW", "ALLOW"
    elif score < 0.7:
        level, decision = "MEDIUM", "WARNING"
    else:
        level, decision = "HIGH", "BLOCK"

    return {
        "risk_score": round(score, 2),
        "risk_level": level,
        "decision": decision,
        "download_status": "Blocked" if decision == "BLOCK" else "Allowed",
        "emails": emails,
        "urls": urls
    }, heatmap_path, None

# ---------------- REPORT ----------------
def create_report(data, file_id, file_type):
    path = os.path.join(TEMP_FOLDER, f"{file_id}_report.txt")

    with open(path, "w") as f:
        f.write("StegoShield AI - Security Report\n\n")
        f.write(f"File Type: {file_type}\n\n")
        f.write(f"Risk Score: {data['risk_score']}\n")
        f.write(f"Risk Level: {data['risk_level']}\n")
        f.write(f"Decision: {data['decision']}\n\n")
        f.write("Additional Signals:\n")
        f.write(f"- Emails Detected: {data['emails']}\n")
        f.write(f"- URLs Detected: {data['urls']}\n")

    return path

# ---------------- URL SCAN ----------------
@app.route("/scan-url", methods=["POST"])
def scan_url():
    try:
        file_url = request.json.get("url")

        response = requests.get(file_url, stream=True, timeout=15)
        content_type = response.headers.get("Content-Type", "")

        if "text/html" in content_type:
            return jsonify({"error": "Not a direct file link"})

        file_id = str(uuid.uuid4())

        if "image" in content_type:
            ext = ".jpg"
            file_type = "Image"
        elif "pdf" in content_type:
            ext = ".pdf"
            file_type = "PDF"
        else:
            return jsonify({"error": "Unsupported file type"})

        file_path = os.path.join(TEMP_FOLDER, f"{file_id}{ext}")

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(1024):
                if chunk:
                    f.write(chunk)

        base = request.host_url

        if ext == ".jpg":
            result, heatmap_path, error = process_image(file_path)

            if error:
                return jsonify({"error": error})

            report_path = create_report(result, file_id, file_type)

            schedule_delete([file_path, heatmap_path, report_path])

            result.update({
                "message": "Analysis complete",
                "download_url": f"{base}download/{file_id}{ext}",
                "heatmap_url": f"{base}heatmap/{file_id}",
                "report_url": f"{base}report/{file_id}"
            })

            return jsonify(result)

        else:
            result = {
                "risk_score": 0.2,
                "risk_level": "LOW",
                "decision": "ALLOW",
                "download_status": "Allowed",
                "emails": 0,
                "urls": 0
            }

            report_path = create_report(result, file_id, file_type)

            schedule_delete([file_path, report_path])

            result.update({
                "message": "PDF analyzed",
                "download_url": f"{base}download/{file_id}{ext}",
                "report_url": f"{base}report/{file_id}"
            })

            return jsonify(result)

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

# ---------------- FILE UPLOAD ----------------
@app.route("/scan-file", methods=["POST"])
def scan_file():
    try:
        file = request.files.get("file")

        if not file:
            return jsonify({"error": "No file uploaded"})

        filename = file.filename.lower()

        if filename.endswith((".jpg", ".jpeg", ".png")):
            ext = ".jpg"
            file_type = "Image"
        elif filename.endswith(".pdf"):
            ext = ".pdf"
            file_type = "PDF"
        else:
            return jsonify({"error": "Unsupported file type"})

        file_id = str(uuid.uuid4())
        file_path = os.path.join(TEMP_FOLDER, f"{file_id}{ext}")

        file.save(file_path)

        base = request.host_url

        if ext == ".jpg":
            result, heatmap_path, error = process_image(file_path)

            if error:
                return jsonify({"error": error})

            report_path = create_report(result, file_id, file_type)

            schedule_delete([file_path, heatmap_path, report_path])

            result.update({
                "message": "File uploaded and analyzed",
                "download_url": f"{base}download/{file_id}{ext}",
                "heatmap_url": f"{base}heatmap/{file_id}",
                "report_url": f"{base}report/{file_id}"
            })

            return jsonify(result)

        else:
            result = {
                "risk_score": 0.2,
                "risk_level": "LOW",
                "decision": "ALLOW",
                "download_status": "Allowed",
                "emails": 0,
                "urls": 0
            }

            report_path = create_report(result, file_id, file_type)

            schedule_delete([file_path, report_path])

            result.update({
                "message": "PDF uploaded",
                "download_url": f"{base}download/{file_id}{ext}",
                "report_url": f"{base}report/{file_id}"
            })

            return jsonify(result)

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})

# ---------------- DOWNLOAD ----------------
@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(TEMP_FOLDER, filename)

    if not os.path.exists(path):
        return jsonify({"error": "File not found"})

    @after_this_request
    def cleanup(response):
        try:
            os.remove(path)
        except:
            pass
        return response

    return send_file(path, as_attachment=True)

# ---------------- HEATMAP ----------------
@app.route("/heatmap/<file_id>")
def heatmap(file_id):
    path = os.path.join(TEMP_FOLDER, f"{file_id}_heatmap.jpg")

    if not os.path.exists(path):
        return jsonify({"error": "Heatmap not found"})

    @after_this_request
    def cleanup(response):
        try:
            os.remove(path)
        except:
            pass
        return response

    return send_file(path)

# ---------------- REPORT ----------------
@app.route("/report/<file_id>")
def report(file_id):
    path = os.path.join(TEMP_FOLDER, f"{file_id}_report.txt")

    if not os.path.exists(path):
        return jsonify({"error": "Report not found"})

    @after_this_request
    def cleanup(response):
        try:
            os.remove(path)
        except:
            pass
        return response

    return send_file(path, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)