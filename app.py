from flask import Flask, render_template, request
from cryptography.fernet import Fernet
import re

app = Flask(__name__)

# Load Fernet key (server-only)
with open("fernet_key.txt", "rb") as f:
    FERNET_KEY = f.read()
fernet = Fernet(FERNET_KEY)

def format_log(raw_log):
    """
    Correctly process decrypted log string:
    - (backspace_xN) -> <del>deleted text</del> (with a space after)
    - (esc) -> <strong>END</strong>
    - (shift) -> (left shift)
    - (shift r) -> (right shift)
    - Capital letters preserved
    """
    output = []
    typed_buffer = []

    pattern = re.compile(r"\((.*?)\)")
    i = 0
    while i < len(raw_log):
        match = pattern.match(raw_log, i)
        if match:
            key_name = match.group(1)
            i = match.end()

            # Flush typed_buffer if a special key happens
            if typed_buffer:
                output.append("".join(typed_buffer))
                typed_buffer = []

            if key_name.startswith("backspace_x"):
                count = int(key_name.split("_x")[1])
                deleted = []
                for _ in range(count):
                    if output:
                        deleted_char = output.pop()
                        deleted.append(deleted_char)
                if deleted:
                    output.append(f"<del>{''.join(deleted[::-1])}</del> ")

            elif key_name == "backspace":
                if output:
                    deleted_char = output.pop()
                    output.append(f"<del>{deleted_char}</del> ")

            elif key_name == "esc":
                output.append(" <strong>END</strong> ")

            elif key_name.lower() == "shift":
                output.append(" (left shift) ")
            elif key_name.lower() == "shift r":
                output.append(" (right shift) ")

            else:
                output.append(f"({key_name})")

        else:
            typed_buffer.append(raw_log[i])
            i += 1

    # Flush any remaining typed_buffer
    if typed_buffer:
        output.append("".join(typed_buffer))

    return "".join(output)

@app.route("/", methods=["GET"])
def upload_page():
    return render_template("upload.html")

@app.route("/view", methods=["POST"])
def view_log():
    uploaded_file = request.files.get("logfile")

    if not uploaded_file:
        return "No file uploaded", 400

    decrypted_lines = []
    for line in uploaded_file:
        line = line.strip()
        if not line:
            continue
        decrypted = fernet.decrypt(line).decode("utf-8")
        decrypted_lines.append(decrypted)

    raw_log = "".join(decrypted_lines)
    formatted_log = format_log(raw_log)

    return render_template("view.html", log=formatted_log)

if __name__ == "__main__":
    app.run(debug=True)
