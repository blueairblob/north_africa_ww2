"""`python -m arena` -- run the local application server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("arena.server:app", host="127.0.0.1", port=8000)
