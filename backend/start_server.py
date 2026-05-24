import uvicorn
import sys
sys.path.insert(0, '.')

if __name__ == "__main__":
    print("Starting server on port 8000...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
