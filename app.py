from flask import Flask, request, render_template, Response, jsonify, url_for
from threading import RLock
import os
import base64
import json
import uuid
import shelve
import tempfile

app = Flask(__name__)
lock = RLock()

return_to = ""

@app.route('/notes/<notes>')
def home(notes):
    return_to = request.args.get("return_to")
    with shelve.open(tempfile.gettempdir() + "/" + notes) as db:
        db["return_to"] = return_to

    return render_template("index.html", id=notes)

@app.route('/api/notes/push', methods=["POST"])
def push_notes():
    ref_id = str(uuid.uuid4())
    with shelve.open(tempfile.gettempdir() + "/" + ref_id) as db:
        base64data = str(request.data.decode())
        print("got base64 data", base64data)
        if base64data != "":
            notes = json.loads(base64.b64decode(base64data))
        else:
            notes = []

        db[ref_id] = (notes, [])

    return jsonify({"url": url_for('home', notes=ref_id, _external=True)}), 200

@app.route('/api/notes/fetch', methods=["GET", "POST"])
def fetch_notes():
    ref_id = str(request.args.get("id"))
    with shelve.open(tempfile.gettempdir() + "/" + ref_id) as db:
        if request.method == "GET":
            return jsonify(db[ref_id][0])
        else:
            notes = db[ref_id][0]
            notes_to_push = db[ref_id][1]
            current_by_index = {note[0]: note for note in notes}

            new_notes = request.json
            for new_note in new_notes:
                new_index = new_note[0]
                new_text = new_note[2]

                old_note = current_by_index.get(new_index)
                if old_note:
                    if old_note[2] != new_text:
                    # Edited text
                        note = [new_index, new_note[1], new_text]
                        notes_to_push.append(note)
                    elif old_note[0] != new_index:
                        # Index changed?
                        note = [new_index, new_note[1], old_note[2]]
                        notes_to_push.append(note)
                        note = [old_note[0], 0, new_text]
                        notes_to_push.append(note)
                else:
                    # New note
                    note = [new_index, 0, new_text]
                    notes_to_push.append(note)

            new_notes_by_index = {note[0]: note for note in notes_to_push}
            if len(notes) == 0:
                notes = notes_to_push
            else:
                for note in notes:
                    enote = new_notes_by_index.get(note[0])
                    if enote:
                        if enote[2] != note[2] or enote[0] != note[0]:
                            notes[note[0]] = enote

            db[ref_id] = (notes, notes_to_push)

        return Response(status=200)

@app.route('/api/encode')
def encode():
    ref_id = str(request.args.get("id"))
    db = shelve.open(tempfile.gettempdir() + "/" + ref_id, writeback=True)
    return_to = db["return_to"]
    # Encode all of the data to the format our app expects
    data = base64.b64encode(json.dumps(db[ref_id][1]).encode())
    print("encoded data is now", data)
    db.clear()
    db.close()

    print("file path is", tempfile.gettempdir() + "/" + ref_id)
    print("does it exist?", os.path.exists(tempfile.gettempdir() + "/" + ref_id))
    os.remove(tempfile.gettempdir() + "/" + ref_id)

    if return_to is None:
        return "pebblejs://close#" + data.decode()

    print("return to is", return_to)
    return return_to + data.decode()

if __name__ == '__main__':
    app.run(debug = True)
