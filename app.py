import socket
import json
import os

PORT = 8080
saved = []


class Request:
    def __init__(self, text):
        top, _, self.body = text.partition("\r\n\r\n")
        lines = top.split("\r\n")

        self.method, target, self.version = lines[0].split(" ")
        self.path, _, query = target.partition("?")

        self.params = {}
        for pair in query.split("&"):
            key, _, value = pair.partition("=")
            if key:
                self.params[key] = value

        self.headers = {}
        for line in lines[1:]:
            key, _, value = line.partition(":")
            self.headers[key.strip().lower()] = value.strip()


def answer(status, content, content_type="text/html"):
    if type(content) is str:
        content = content.encode()
    lines = [
        "HTTP/1.1 " + status,
        "Content-Type: " + content_type,
        "Content-Length: " + str(len(content)),
        "Connection: close",
        "",
        "",
    ]
    return "\r\n".join(lines).encode() + content


def send_json(data, status="200 OK"):
    return answer(status, json.dumps(data), "application/json")


def open_file(name):
    path = os.path.join("public", name)
    if not os.path.isfile(path):
        return answer("404 Not Found", "<h1>Nothing here</h1>")
    with open(path, "rb") as f:
        data = f.read()
    kind = "text/css" if name.endswith(".css") else "text/html"
    return answer("200 OK", data, kind)


def home(req):
    return open_file("index.html")


def page(req):
    number = req.params.get("id", "?")
    return answer("200 OK", f"<h1>Page number {number}</h1><p>Params: {req.params}</p>")


def list_items(req):
    return send_json(saved)


def add_item(req):
    if req.headers.get("content-type") != "application/json":
        return answer("400 Bad Request", "Send JSON please")
    item = json.loads(req.body)
    saved.append(item)
    return send_json({"saved": item}, "201 Created")


routes = {
    ("GET", "/"): home,
    ("GET", "/page"): page,
    ("GET", "/items"): list_items,
    ("POST", "/items"): add_item,
}


def handle(client):
    raw = client.recv(4096).decode()
    if raw:
        req = Request(raw)

        size = int(req.headers.get("content-length", 0))
        while len(req.body.encode()) < size:
            req.body += client.recv(4096).decode()

        print(req.method, req.path, req.params)
        print(req.headers)
        if req.body:
            print(req.body)

        action = routes.get((req.method, req.path))
        if action:
            reply = action(req)
        elif req.method == "GET":
            reply = open_file(req.path.lstrip("/"))
        else:
            reply = answer("404 Not Found", "Unknown route")

        client.sendall(reply)
    client.close()


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("localhost", PORT))
    s.listen()
    print("Listening on port", PORT)
    while True:
        client, address = s.accept()
        handle(client)
