from flask import Flask, request, render_template, Response, jsonify, url_for
import base64
import json
import uuid

app = Flask(__name__)

notesdata = {}
notes = []
notes_to_push = []
return_to = ""

@app.route('/notes/<notes>')
def home(notes):
    global return_to
    return render_template("index.html", id=notes)

@app.route('/api/notes/push', methods=["POST"])
def push_notes():
    base64data = request.data.decode()
    notes = json.loads(base64.b64decode(base64data))
    ref_id = str(uuid.uuid4())
    notesdata[ref_id] = (notes, [])

    return jsonify({"url": url_for('home', notes=ref_id, _external=True)}), 200

@app.route('/api/notes/fetch', methods=["GET", "POST"])
def fetch_notes():
    global notesdata
    ref_id = str(request.args.get("id"))
    print("reference ID is", ref_id)
    if request.method == "GET":
        print(notesdata.get(ref_id))
        return notesdata.get(ref_id)[0]
    else:
        print("testing before doing anything", notesdata.get(ref_id)[0])
        notes = notesdata.get(ref_id)[0]
        notes_to_push = notesdata.get(ref_id)[1]
        current_by_index = {note[0]: note for note in notesdata[ref_id][0]}

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
        for note in notes:
            enote = new_notes_by_index.get(note[0])
            if enote:
                if enote[2] != note[2] or enote[0] != note[0]:
                    notes[note[0]] = enote

        notesdata[ref_id] = (notes, notes_to_push)

        print("New notes are", notesdata[ref_id][0])
        print("modified notes were", notes_to_push)
        return Response(status=200)

@app.route('/api/encode')
def encode():
    ref_id = str(request.args.get("id"))
    # Encode all of the data to the format our app expects
    data = base64.b64encode(json.dumps(notesdata[ref_id][1]).encode())
    notesdata[ref_id] = ()

    if return_to is None:
        return "pebblejs://close#" + data.decode()

    return return_to + data.decode()

if __name__ == '__main__':
    app.run(debug = True)
