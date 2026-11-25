import asyncio
import os
import re

PUBLIC_PORT = int(os.environ.get("PORT", 80))
NGINX_HOST = "127.0.0.1"
NGINX_PORT = 8080
XRAY_PATHS = ("/trojan", "/vless", "/vmess", "/trojan-httpup", "/vless-httpup", "/vmess-httpup")

async def pipe(reader, writer):
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
                clean_request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"{host_header}\r\n"
                    f"Upgrade: websocket\r\n"
                    f"Connection: Upgrade\r\n\r\n"
                ).encode("latin-1")

                up_reader, up_writer = await asyncio.open_connection(NGINX_HOST, NGINX_PORT)
                up_writer.write(clean_request)
                await up_writer.drain()

                up_resp = await up_reader.readuntil(b"\r\n\r\n")
                client_writer.write(up_resp)
                await client_writer.drain()

                await asyncio.sleep(0.05)
                if client_reader._buffer:
                    buf = bytes(client_reader._buffer)
                    cleaned = re.sub(rb"^HTTP/[^\r\n]*\r\n\r\n", b"", buf)
                    client_reader._buffer.clear()
                    if cleaned:
                        up_writer.write(cleaned)
                        await up_writer.drain()

                await asyncio.gather(
                    pipe(client_reader, up_writer),
                    pipe(up_reader, client_writer),
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
