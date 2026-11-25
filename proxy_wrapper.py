import asyncio
import os
import re

PUBLIC_PORT = int(os.environ.get("PORT", 8080))
NGINX_HOST = "127.0.0.1"
NGINX_PORT = 8081
XRAY_PATHS = (
    "/xhttp", "/httpup", "/vless",
    "/vmess-xhttp", "/vmess-httpup", "/vmess",
    "/trojan-xhttp", "/trojan-httpup", "/trojan"
)

async def pipe_client_to_up(reader, writer):
    first_chunk = True
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            if first_chunk:
                first_chunk = False
                data = re.sub(rb"^HTTP/[^\r\n]*\r\n\r\n", b"", data)
                if not data:
                    continue
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass

async def pipe_up_to_client(reader, writer):
    try:
        while True:
            data = await reader.read(8192)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass

async def handle_client(client_reader, client_writer):
    try:
        while True:
            raw_head = await client_reader.readuntil(b"\r\n\r\n")
            text_head = raw_head.decode("latin-1", errors="ignore")
            lines = text_head.split("\r\n")
            first_line = lines[0]

            if first_line.startswith("HTTP/"):
                continue

            parts = first_line.split(" ")
            path = parts[1] if len(parts) >= 2 else "/"

            if any(path.startswith(p) for p in XRAY_PATHS):
                host_header = next((l for l in lines if l.lower().startswith("host:")), "Host: localhost")
                ws_headers = [l for l in lines[1:] if l.lower().startswith("sec-websocket-")]
                if not any(h.lower().startswith("sec-websocket-key:") for h in ws_headers):
                    ws_headers.append("Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==")
                if not any(h.lower().startswith("sec-websocket-version:") for h in ws_headers):
                    ws_headers.append("Sec-WebSocket-Version: 13")
                extra = "\r\n".join(ws_headers) + "\r\n"
                clean_request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"{host_header}\r\n"
                    f"Upgrade: websocket\r\n"
                    f"Connection: Upgrade\r\n"
                    f"{extra}\r\n"
                ).encode("latin-1")

                up_reader, up_writer = await asyncio.open_connection(NGINX_HOST, NGINX_PORT)
                up_writer.write(clean_request)
                await up_writer.drain()

                up_resp = await up_reader.readuntil(b"\r\n\r\n")
                client_writer.write(up_resp)
                await client_writer.drain()

                if client_reader._buffer:
                    buf = bytes(client_reader._buffer)
                    cleaned = re.sub(rb"^HTTP/[^\r\n]*\r\n\r\n", b"", buf)
                    client_reader._buffer.clear()
                    if cleaned:
                        up_writer.write(cleaned)
                        await up_writer.drain()

                await asyncio.gather(
                    pipe_client_to_up(client_reader, up_writer),
                    pipe_up_to_client(up_reader, client_writer),
                )
                return
            else:
                client_writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: keep-alive\r\n\r\n")
                await client_writer.drain()
    except Exception:
        try:
            client_writer.close()
        except Exception:
            pass

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", PUBLIC_PORT)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
